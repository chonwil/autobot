from abc import ABC, abstractmethod
from typing import List, Dict, Any
from shared.lib.llm_usage import LLMUsage
from loguru import logger
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langsmith import traceable

class BaseRAG(ABC):
    def __init__(self):
        self.name: str = self.__class__.__name__
        self.description: str = "Base RAG implementation"
        self.conversation_history: List[Dict[str, str]] = []
        self.usage: LLMUsage = LLMUsage(node_title=self.name)
        self.logs: List[str] = []
        
        # Initialize LangChain components
        self.llm = ChatOpenAI(temperature=0, model='gpt-3.5-turbo')
        self.output_parser = StrOutputParser()

    @abstractmethod
    def _retrieve_relevant_context(self, query: str) -> str:
        """
        Abstract method to be implemented by subclasses.
        This method should retrieve relevant context based on the query.
        """
        pass

    @traceable(name="query")
    def _query(self, query: str) -> str:
        """
        Core RAG logic to be used by all subclasses.
        """
        context = self._retrieve_relevant_context(query)
        prompt = self._prepare_prompt(query, context)
        
        chain = (
            {"context": RunnablePassthrough(), "query": RunnablePassthrough()}
            | prompt
            | self.llm
            | self.output_parser
        )
        
        response = chain.invoke({"context": context, "query": query})
        processed_response = self._process_response(response)
        return processed_response

    @traceable(name="greet")
    def greet(self, user_name: str) -> str:
        """
        Generate a greeting message for the user.
        """
        greeting = f"Hola {user_name}! Soy {self.name}. En que te puedo ayudar?"
        self.conversation_history.append(AIMessage(content=greeting))
        return greeting

    @traceable(name="chat")
    def chat(self, message: str) -> str:
        """
        Process a user message and return a response.
        """
        self.conversation_history.append(HumanMessage(content=message))
        
        try:
            response = self._query(message)
            self.conversation_history.append(AIMessage(content=response))
            return response
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            logger.error(error_message)
            self.logs.append(error_message)
            return "Lo lamento, pero acaba de ocurrir un error, podrías intentar nuevamente?"

    def get_logs(self) -> str:
        """
        Return the logs as a string.
        """
        return "\n".join(self.logs)

    def get_usage(self) -> LLMUsage:
        """
        Return the LLM usage metrics.
        """
        return self.usage

    def reset(self):
        """
        Reset the conversation history, usage metrics, and logs.
        """
        self.conversation_history = []
        self.usage = LLMUsage(node_title=self.name)
        self.logs = []

    def _log(self, message: str, level: str = "INFO"):
        """
        Add a log message and print it.
        """
        self.logs.append(message)
        logger.log(level, message)

    def _update_usage(self, new_usage: LLMUsage):
        """
        Update the usage metrics.
        """
        self.usage.add_usage(new_usage)

    def _prepare_prompt(self, query: str, context: str) -> ChatPromptTemplate:
        """
        Prepare the prompt for the LLM based on the conversation history, query, and context.
        """
        template = """You are an AI assistant. Use the following context to answer the user's question:

Context: {context}

User's question: {query}

Please provide a concise and accurate answer, in Spanish, based on the given context:
"""
        return ChatPromptTemplate.from_template(template)

    def _process_response(self, response: str) -> str:
        """
        Process the raw LLM response. Can be overridden by subclasses if needed.
        """
        return response.strip()