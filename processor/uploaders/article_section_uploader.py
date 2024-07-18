import json
import os
from typing import List, Dict, Any, Optional
from lib.embeddings import AutobotEmbedding
from lib.pinecone_uploader import PineconeUploader
from loguru import logger
            
class ArticleSectionUploader(PineconeUploader):
    def __init__(self, **kwargs):
        super().__init__(entity="articles", **kwargs)

    def _get_items(self, limit: Optional[int]) -> List[Dict[str, Any]]:
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

    def _process_item(self, article: Dict[str, Any]):
        output_file = os.path.join(self.output_dir, f"article_{article['article_id']}_embeddings.json")
        
        if os.path.exists(output_file) or os.path.exists(output_file.replace("processed", "uploaded")):
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
                AutobotEmbedding(
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