import json
import os
import queue
from typing import List, Dict, Any, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from lib.processor_result import ProcessorResult
from lib.embeddings import ArticleSectionEmbedding
from shared.utils import DBHelper
from loguru import logger
from concurrent.futures import ThreadPoolExecutor
            
class ArticleSectionUploader:
    def __init__(self, company: str = "openai", model_name: str = "text-embedding-3-small", dimensions: int = 1536):
        self.company = company
        self.model_name = model_name
        self.dimensions = dimensions
        self.db = DBHelper()
        self.embeddings = OpenAIEmbeddings(model=model_name)
        self.output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'shared', 'tmp', 'processed_embeddings')
        self.results = None
        os.makedirs(self.output_dir, exist_ok=True)
        self.work_queue = queue.Queue()
        self.results = None

    def prepare(self, limit: Optional[int] = None, num_threads: int = 20):
        self.results = ProcessorResult(action="upload-prepare", entity="articles")
        articles = self._get_articles(limit)
        
        # Populate the work queue
        for article in articles:
            self.work_queue.put(article)

        # Create and start worker threads
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            for _ in range(num_threads):
                executor.submit(self._worker)

        logger.info(f"Prepare complete. {self.results.items_processed} articles processed.")
        return self.results

    def _worker(self):
        while True:
            try:
                article = self.work_queue.get_nowait()
                self._process_article(article)
                self.work_queue.task_done()
            except queue.Empty:
                break

    def _get_articles(self, limit: Optional[int]) -> List[Dict[str, Any]]:
        query = """
            SELECT DISTINCT a.id as article_id, a.title as article_title, p.url as article_url
            FROM articles a
            JOIN posts p ON a.post_id = p.id
            JOIN article_sections asec ON a.id = asec.article_id
        """
        if limit:
            query += f" LIMIT {limit}"
        return self.db.execute_query(query)

    def _get_article_sections(self, article_id: int) -> List[Dict[str, Any]]:
        query = """
            SELECT asec.title as section_title, asec.content
            FROM article_sections asec
            WHERE asec.article_id = %s
        """
        return self.db.execute_query(query, (article_id,))

    def _process_article(self, article: Dict[str, Any]):
        output_file = os.path.join(self.output_dir, f"article_{article['article_id']}_embeddings.json")
        
        if os.path.exists(output_file):
            logger.info(f"Embeddings for article {article['article_id']} already exist. Skipping.")
            return

        sections = self._get_article_sections(article['article_id'])
        all_embeddings = []

        for section in sections:
            chunks = self._generate_chunks(section['content'])
            embeddings = self._generate_embeddings(chunks)

            metadata = {
                "article_title": article['article_title'],
                "article_url": article['article_url'],
                "section_title": section['section_title']
            }

            section_embeddings = [
                ArticleSectionEmbedding(
                    chunk=chunk,
                    embedding=embedding,
                    metadata=metadata,
                    company=self.company,
                    model_name=self.model_name,
                    dimensions=self.dimensions
                ).to_dict()
                for chunk, embedding in zip(chunks, embeddings)
            ]
            all_embeddings.extend(section_embeddings)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_embeddings, f, ensure_ascii=False, indent=2)

        logger.info(f"Embeddings for article {article['article_id']} saved to {output_file}")
        self.results.items_processed += 1

    def _generate_chunks(self, text: str) -> List[str]:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            length_function=len,
        )
        return text_splitter.split_text(text)

    def _generate_embeddings(self, chunks: List[str]) -> List[List[float]]:
        return self.embeddings.embed_documents(chunks)