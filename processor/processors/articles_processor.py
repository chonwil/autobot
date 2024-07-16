import json
import time
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.pydantic_v1 import BaseModel, Field
from langchain_core.language_models.base import BaseLanguageModel
from langchain_community.callbacks.manager import get_openai_callback
from shared.utils import DBHelper
from lib.processor_result import ProcessorResult
from loguru import logger
from shared.lib.llm_usage import LLMUsage
import tiktoken

class ArticleAnalysis(BaseModel):
    summary: str = Field(description="Summary of the author's impression of the car being evaluated, up to 100 words in Spanish")
    sentiment_score: float = Field(description="Sentiment score from -1 (negative) to 1 (positive)")
    sentiment_evidence: List[str] = Field(description="Up to 5 sentences extracted from the original text that best support the sentiment. The sentences should be present in the content.")
    sentiment_emotions: List[str] = Field(description="3 emotions expressed in the article")
    comments_sentiment_score: float = Field(description="Comments sentiment score from -1 (negative) to 1 (positive)")
    comments_summary: str = Field(description="Summary, up to 100 words, of overall impressions from commenters about the car, in Spanish")

class SectionAnalysis(BaseModel):
    summary: str = Field(description="Summary of the author's impression of the car features being evaluated, up to 50 words, in Spanish")
    sentiment_score: float = Field(description="Sentiment score from -1 (negative) to 1 (positive)")
    # sentiment_evidence: str = Field(description="A sentence extracted from the text that best supports the sentiment. The sentence should be present in the content.")
    # sentiment_emotions: List[str] = Field(description="3 emotions expressed in the section")

class LLMConfig:
    DEFAULT_COMPANY = "openai"
    DEFAULT_MODEL = "gpt-3.5-turbo"
    DEFAULT_TEMPERATURE = "0"

class ArticlesProcessor:
    def __init__(self):
        self.db = DBHelper()
        self.article_parser = PydanticOutputParser(pydantic_object=ArticleAnalysis)
        self.section_parser = PydanticOutputParser(pydantic_object=SectionAnalysis)
        self.llm_usage = LLMUsage(node_title="ArticlesProcessor")
        self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")

    def process(self, company_name: str = LLMConfig.DEFAULT_COMPANY, 
                model_name: str = LLMConfig.DEFAULT_MODEL, 
                num_articles: int = 0) -> ProcessorResult:
        result = ProcessorResult(action="process", entity="articles")
        self.llm_usage = LLMUsage(node_title="ArticlesProcessor")
        llm = self._get_llm(company_name, model_name)
        articles = self._get_unprocessed_articles(num_articles)
        
        for article in articles:
            try:
                logger.info(f"Processing article: {article['id']} - {article['title']}")
                processed, usage = self._process_article(article, llm, company_name, model_name)
                self.llm_usage.add_usage(usage)
                if processed:
                    section_usage = self._process_article_sections(article['id'], llm, company_name, model_name)
                    self.llm_usage.add_usage(section_usage)
                    result.items_processed += 1
            except Exception as e:
                logger.error(f"Error processing article {article['id']}: {str(e)}")
        
        result.llm_usage.add_usage(self.llm_usage)
        return result

    def _get_llm(self, company_name: str, model_name: str) -> BaseLanguageModel:
        if company_name == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=model_name, temperature=LLMConfig.DEFAULT_TEMPERATURE)
        elif company_name == "groq":
            from langchain_groq import ChatGroq
            return ChatGroq(model=model_name, temperature=LLMConfig.DEFAULT_TEMPERATURE)
        elif company_name == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(model=model_name, temperature=LLMConfig.DEFAULT_TEMPERATURE)
        else:
            raise ValueError(f"LLM provider {company_name} not supported")

    def _get_unprocessed_articles(self, limit: int = 0) -> List[Dict[str, Any]]:
        query = """
            SELECT id, title, content, comments
            FROM articles
            WHERE date_processed IS NULL
            ORDER BY id ASC
        """
        if limit > 0:
            query += f" LIMIT {limit}"
        return self.db.execute_query(query)

    def _process_article(self, article: Dict[str, Any], llm: BaseLanguageModel, 
                         company_name: str, model_name: str) -> Tuple[bool, LLMUsage]:
        usage = LLMUsage(action="process_article", model_name=model_name)
        start_time = time.time()
        
        try:
            prompt = self._create_article_prompt()
            chain = prompt | llm | self.article_parser
            
            output = self._invoke_chain(chain, article['content'], article['comments'], company_name, model_name, usage, is_article=True)
            usage.time = time.time() - start_time
            logger.info(usage.get_summary())
            
            self._update_article(article['id'], output.dict())
            logger.info(f"Article processed: {article['id']}")
            
            return True, usage
        except Exception as e:
            logger.error(f"Error processing article {article['id']}: {str(e)}")
            usage.time = time.time() - start_time
            return False, usage

    def _process_article_sections(self, article_id: int, llm: BaseLanguageModel, 
                                  company_name: str, model_name: str) -> LLMUsage:
        sections = self._get_article_sections(article_id)
        usage = LLMUsage(node_title="process_article_sections", model_name=model_name)
        if sections:
            logger.info(f"Processing {len(sections)} sections")
        
        for section in sections:
            section_usage = LLMUsage(action="process_article_section", model_name=model_name)
            start_time = time.time()
            
            try:
                prompt = self._create_section_prompt()
                chain = prompt | llm | self.section_parser
                
                output = self._invoke_chain(chain, section['content'], None, company_name, model_name, section_usage, is_article=False)
                
                self._update_article_section(section['id'], output.dict())
                logger.info(f"Section processed: {section['title']}")
                
                section_usage.time = time.time() - start_time
                logger.info(section_usage.get_summary())
            except Exception as e:
                logger.error(f"Error processing article section {section['id']}: {str(e)}")
                section_usage.time = time.time() - start_time
                
            usage.add_usage(section_usage)
        return usage

    def _create_article_prompt(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            ("system", "Analyze the following content and provide a summary, sentiment analysis, and comment analysis in Spanish. {format_instructions}"),
            ("human", "{content}\n\nComments:\n{comments}")
        ])

    def _create_section_prompt(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            ("system", "Analyze the following content and provide a summary and sentiment analysis in Spanish. {format_instructions}"),
            ("human", "{content}")
        ])

    def _invoke_chain(self, chain, content: str, comments: Optional[str], company_name: str, model_name: str, usage: LLMUsage, is_article: bool, is_truncated: bool = False):
        try:
            input_data = self._prepare_input(content, comments, is_article)
            
            if company_name == "openai":
                with get_openai_callback() as cb:
                    output = chain.invoke(input_data)
                    usage.token_input = cb.prompt_tokens
                    usage.token_output = cb.completion_tokens
                    usage.cost = cb.total_cost
            else:
                output = chain.invoke(input_data)
                usage.set_estimated_token_usage_and_cost(company_name, model_name, content + " " + (comments or ""), str(output))
            
            return output
        except Exception as e:
            if "context_length_exceeded" in str(e) and not is_truncated:
                truncated_input = self._truncate_input(input_data, model_name)
                return self._invoke_chain(chain, truncated_input["content"], truncated_input.get("comments"), company_name, model_name, usage, is_article, is_truncated=True)
            else:
                raise

    def _prepare_input(self, content: str, comments: Optional[str], is_article: bool) -> Dict[str, Any]:
        input_dict = {
            "content": content,
            "format_instructions": self.article_parser.get_format_instructions() if is_article else self.section_parser.get_format_instructions()
        }
        if comments and is_article:
            input_dict["comments"] = comments
        return input_dict

    def _truncate_input(self, input_data: Dict[str, Any], model_name: str) -> Dict[str, Any]:
        max_tokens = 14000  # Leave some buffer for the model's response
        current_tokens = len(self.tokenizer.encode(input_data["content"] + input_data.get("comments", "")))
        
        if current_tokens > max_tokens:
            content_tokens = len(self.tokenizer.encode(input_data["content"]))
            comments_tokens = len(self.tokenizer.encode(input_data.get("comments", "")))
            
            # Determine how much to truncate from content and comments
            total_excess = current_tokens - max_tokens
            content_excess = min(total_excess, int(total_excess * (content_tokens / current_tokens)))
            comments_excess = total_excess - content_excess
            
            # Truncate content
            if content_excess > 0:
                content_token_ids = self.tokenizer.encode(input_data["content"])
                truncated_content_tokens = content_token_ids[:-(content_excess + 1)]  # +1 to be safe
                input_data["content"] = self.tokenizer.decode(truncated_content_tokens)
            
            # Truncate comments if present
            if "comments" in input_data and comments_excess > 0:
                comments_token_ids = self.tokenizer.encode(input_data["comments"])
                truncated_comments_tokens = comments_token_ids[:-(comments_excess + 1)]  # +1 to be safe
                input_data["comments"] = self.tokenizer.decode(truncated_comments_tokens)
        
        return input_data

    def _get_article_sections(self, article_id: int) -> List[Dict[str, Any]]:
        return self.db.execute_query("""
            SELECT id, title, content
            FROM article_sections
            WHERE article_id = %s AND date_processed IS NULL
        """, (article_id,))

    def _update_article(self, article_id: int, analysis: Dict[str, Any]):
        self.db.update('articles', {'id': article_id}, {
            'summary': analysis['summary'],
            'sentiment_score': analysis['sentiment_score'],
            'sentiment_evidence': json.dumps(analysis['sentiment_evidence'], ensure_ascii=False),
            'sentiment_emotions': json.dumps(analysis['sentiment_emotions'], ensure_ascii=False),
            'comments_sentiment_score': analysis['comments_sentiment_score'],
            'comments_summary': analysis['comments_summary'],
            'date_processed': datetime.now()
        })

    def _update_article_section(self, section_id: int, analysis: Dict[str, Any]):
        self.db.update('article_sections', {'id': section_id}, {
            'summary': analysis['summary'],
            'sentiment_score': analysis['sentiment_score'],
            # 'sentiment_evidence': json.dumps(analysis['sentiment_evidence'], ensure_ascii=False),
            # 'sentiment_emotions': json.dumps(analysis['sentiment_emotions'], ensure_ascii=False),
            'date_processed': datetime.now()
        })

    