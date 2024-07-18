import json
import os
from typing import List, Dict, Any, Optional
from lib.embeddings import AutobotEmbedding
from lib.pinecone_uploader import PineconeUploader
from loguru import logger

class LaunchUploader(PineconeUploader):
    def __init__(self, **kwargs):
        super().__init__(entity="launches", **kwargs)

    def _get_items(self, limit: Optional[int]) -> List[Dict[str, Any]]:
        query = """
            SELECT l.id as launch_id, l.title as launch_title, p.url as launch_url, l.content as launch_content
            FROM launches l
            JOIN posts p ON l.post_id = p.id
        """
        if limit:
            query += f" LIMIT {limit}"
        return self.db.execute_query(query)

    def _process_item(self, launch: Dict[str, Any]):
        output_file = os.path.join(self.output_dir, f"launch_{launch['launch_id']}_embeddings.json")
        
        if os.path.exists(output_file):
            logger.info(f"Embeddings for launch {launch['launch_id']} already exist. Skipping.")
            return

        chunks = self._generate_chunks(launch['launch_content'])
        embeddings = self._generate_embeddings(chunks)

        metadata = {
            "launch_title": launch['launch_title'],
            "launch_url": launch['launch_url']
        }

        launch_embeddings = [
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

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(launch_embeddings, f, ensure_ascii=False, indent=2)

        logger.info(f"Embeddings for launch {launch['launch_id']} saved to {output_file}")
        self.results.items_processed += 1