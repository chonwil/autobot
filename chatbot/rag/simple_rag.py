from typing import List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel, Field
from langsmith import traceable

from chatbot.rag.lib.vector_store_rag import VectorStoreRAG

class MessageClassification(BaseModel):
    category: str = Field(description="The category of the user's message: 'direct_answer' or 'car_question'")
    explanation: str = Field(description="A brief explanation of why this category was chosen")
    direct_answer: Optional[str] = Field(description="A direct answer to the question if this is not a car-related question")

class SimpleRAG(VectorStoreRAG):
    def __init__(self):
        super().__init__()
        self.name = "SimpleRAG"
        self.description = "A simple RAG implementation that can answer directly or query Pinecone for context."
        
        if not self.vectorstore or not self.embeddings:
            raise ValueError("Pinecone initialization failed")


    @traceable(name="context_based_answer")
    def _context_based_answer(self, query: str) -> str:
        context_docs = self._retrieve_relevant_context(query)
        if not context_docs:
            return "Lo siento, no pude encontrar información relevante para responder a tu pregunta."
        
        context_text = "\n".join([doc.page_content for doc in context_docs])
        prompt = self._prepare_prompt(query, context_text)
        
        chain = (
            {"context": RunnablePassthrough(), "query": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )
        
        try:
            response = chain.invoke({"context": context_text, "query": query})
            return self._process_response(response)
        except Exception as e:
            self._log(f"Error generating context-based answer: {str(e)}", "ERROR")
            return "Lo siento, ocurrió un error al procesar tu pregunta. Por favor, inténtalo de nuevo."

    @traceable(name="classify_message")
    def _classify_message(self, message: str) -> MessageClassification:
        classify_prompt = ChatPromptTemplate.from_template(
            """Classify the following user message as a 'car_question' if it is a car-related question, or 'direct_answer' otherwise. If it is not a car related question, answer the question directly and concisely, in Spanish.

            User message: {message}

            Provide your classification and a brief explanation in the following format:
            Category: [Your classification]
            Explanation: [Your explanation]
            Direct answer: [Your direct answer if applicable]
            """
        )
        
        classify_chain = classify_prompt | self.llm | StrOutputParser()
        
        try:
            result = classify_chain.invoke({"message": message})
            lines = result.strip().split('\n')
            category = lines[0].split(': ')[1].strip().lower()
            explanation = lines[1].split(': ')[1].strip()
            direct_answer = lines[2].split(': ')[1].strip() if len(lines) > 2 else None
            
            return MessageClassification(category=category, explanation=explanation, direct_answer=direct_answer)
        except Exception as e:
            self._log(f"Error classifying message: {str(e)}", "ERROR")
            return MessageClassification(category="direct_answer", explanation="Error in classification", direct_answer="Lo siento, no pude entender tu pregunta. ¿Podrías reformularla?")

    def _prepare_prompt(self, query: str, context: str) -> ChatPromptTemplate:
        template = """Eres un asistente de IA para un sitio web de automóviles. Utiliza el siguiente contexto para responder a la pregunta del usuario:

        Contexto:
        {context}

        Pregunta del usuario: {query}

        Por favor, proporciona una respuesta concisa y precisa en español, basada en el contexto dado. Si el contexto no contiene información relevante, 
        di que no tienes suficiente información para responder a la pregunta.
        """
        return ChatPromptTemplate.from_template(template)

    def _query(self, query: str) -> str:
        classification = self._classify_message(query)
        self._log(f"Message classification: {classification.category} - {classification.explanation}")
        
        if classification.category == "direct_answer":
            return self._process_response(classification.direct_answer or "No pude generar una respuesta directa.")
        else:
            return self._context_based_answer(query)