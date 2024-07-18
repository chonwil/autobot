from typing import List
from langchain.schema import Document
from langsmith import traceable
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

from .base_rag import BaseRAG

import os

class VectorStoreRAG(BaseRAG):
    def __init__(self):
        super().__init__()
        
        try:
            pinecone_api_key = os.environ.get("PINECONE_API_KEY")
            if not pinecone_api_key:
                raise ValueError("PINECONE_API_KEY environment variable is not set")
            
            pc = Pinecone(api_key=pinecone_api_key)
            
            index_name = os.environ.get("PINECONE_INDEX")
            if not index_name:
                raise ValueError("PINECONE_INDEX environment variable is not set")
            
            self.index = pc.Index(index_name)
            self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
            self.vectorstore = PineconeVectorStore(index=self.index, embedding=self.embeddings, text_key="chunk")
        except Exception as e:
            self._log(f"Failed to initialize Pinecone: {str(e)}", "ERROR")
            raise

    @traceable(name="retrieve_relevant_context")
    def _retrieve_relevant_context(self, query: str, k: int = 3) -> List[Document]:
        docs = self.vectorstore.similarity_search(query, k=k)
        if not docs:
            self._log("No relevant context found")
        return docs

    def get_relevant_context(self, query: str, k: int = 3) -> str:
        docs = self._retrieve_relevant_context(query, k)
        return "\n".join([doc.page_content for doc in docs])