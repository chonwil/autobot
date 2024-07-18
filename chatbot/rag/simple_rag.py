from typing import List, Optional
from chatbot.rag.base_rag import BaseRAG
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.schema import Document
from pydantic import BaseModel, Field
from pinecone import Pinecone
import os
from langsmith import traceable
from loguru import logger

class MessageClassification(BaseModel):
    category: str = Field(description="The category of the user's message: 'direct_answer' or 'car_question'")
    explanation: str = Field(description="A brief explanation of why this category was chosen")
    direct_answer: Optional[str] = Field(description="A direct answer to the question if this is not a car-related question")

class SimpleRAG(BaseRAG):
    def __init__(self):
        super().__init__()
        self.name = "SimpleRAG"
        self.description = "A simple RAG implementation that can answer directly or query Pinecone for context."
        
        # Initialize Pinecone
        pinecone_api_key = os.environ.get("PINECONE_API_KEY")
        pc = Pinecone(api_key=pinecone_api_key)
        
        self.index_name = os.environ.get("PINECONE_INDEX")
        self.index = pc.Index(self.index_name)
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.vectorstore = PineconeVectorStore(index=self.index, embedding=self.embeddings, text_key="chunk")
        
        # Initialize classifier LLM
        self.classifier_llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo")

    @traceable(name="retrieve_relevant_context")
    def _retrieve_relevant_context(self, query: str) -> List[Document]:
        logger.debug(f"Generating embedding for query: {query}")
        query_embedding = self.embeddings.embed_query(query)
        logger.debug(f"Query embedding shape: {len(query_embedding)}")
        
        logger.debug(f"Performing similarity search with k=3")
        docs = self.vectorstore.similarity_search(query, k=3)
        
        logger.debug(f"Number of documents retrieved: {len(docs)}")
        return docs

    # ... (rest of the methods remain the same)

    @traceable(name="context_based_answer")
    def _context_based_answer(self, query: str) -> str:
        context_docs = self._retrieve_relevant_context(query)
        context_text = "\n".join([doc.page_content for doc in context_docs])
        
        prompt = self._prepare_prompt(query, context_text)
        
        chain = (
            {"context": RunnablePassthrough(), "query": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )
        
        response = chain.invoke({"context": context_text, "query": query})
        
        return self._process_response(response)


    @traceable(name="classify_message")
    def _classify_message(self, message: str) -> MessageClassification:
        classify_prompt = ChatPromptTemplate.from_template(
            """Classify the following user message as a 'car_question' if it is a car-related question, or 'direct_answer' otherwise. If it is not a car related question, answer the question directly and concisely.

            User message: {message}

            Provide your classification and a brief explanation in the following format:
            Category: [Your classification]
            Explanation: [Your explanation]
            Direct answer: [Your direct answer if applicable]
            """
        )
        
        classify_chain = classify_prompt | self.classifier_llm | StrOutputParser()
        
        result = classify_chain.invoke({"message": message})
        
        lines = result.strip().split('\n')
        category = lines[0].split(': ')[1].strip().lower()
        explanation = lines[1].split(': ')[1].strip()
        direct_answer=lines[2].split(': ')[1].strip()
        
        return MessageClassification(category=category, explanation=explanation, direct_answer=direct_answer)

    def _prepare_prompt(self, query: str, context: List[Document]) -> ChatPromptTemplate:
        template = """You are an AI assistant for an automotive website. Use the following context to answer the user's question:

        Context:
        {context}

        User's question: {query}

        Please provide a concise and accurate answer based on the given context. If the context doesn't contain relevant information, 
        say that you don't have enough information to answer the question.
        """
        return ChatPromptTemplate.from_template(template)

    def _query(self, query: str) -> str:
        classification = self._classify_message(query)
        self._log(f"Message classification: {classification.category} - {classification.explanation}")
        
        if classification.category == "direct_answer":
            return self._process_response(classification.direct_answer)
        else:
            return self._context_based_answer(query)