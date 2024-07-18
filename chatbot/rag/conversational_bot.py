from langchain_core.prompts import ChatPromptTemplate
from chatbot.rag.lib.base_rag import BaseRAG

class ConversationalBot(BaseRAG):

    def __init__(self):
        super().__init__()
        self.name = "ConversationalBot"
        self.description = "Bot conversacional que utiliza el historial de chat para responder preguntas."

    def _query(self, query: str) -> str:
        prompt = ChatPromptTemplate.from_template(
            "Usa este historial para responder en español.\n"
            "{history}\n"
            "Usuario: {query}\n"
            "AI:"
        )
        
        chain = prompt | self.llm | self.output_parser
        return chain.invoke({"history": self._format_history(), "query": query})

    def _retrieve_relevant_context(self, query: str) -> str:
        return ""