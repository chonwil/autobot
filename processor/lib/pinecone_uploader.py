import json
import os
import queue
from typing import List, Dict, Any, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from lib.processor_result import ProcessorResult
from lib.embeddings import AutobotEmbedding
from shared.utils import DBHelper
from loguru import logger
from concurrent.futures import ThreadPoolExecutor
from pinecone import Pinecone

class PineconeUploader:
    def __init__(self, entity: str, company: str = "openai", model_name: str = "text-embedding-3-small", dimensions: int = 1536):
        self.entity = entity
        self.company = company
        self.model_name = model_name
        self.dimensions = dimensions
        self.db = DBHelper()
        self.embeddings = OpenAIEmbeddings(model=model_name)
        self.output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'shared', 'tmp', 'processed_embeddings')
        self.uploaded_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'shared', 'tmp', 'uploaded_embeddings')
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.uploaded_dir, exist_ok=True)
        self.results = None
        self.work_queue = queue.Queue()

    def prepare(self, limit: Optional[int] = None, num_threads: int = 20) -> ProcessorResult:
        self.results = ProcessorResult(action="upload-prepare", entity=self.entity)
        items = self._get_items(limit)
        
        for item in items:
            self.work_queue.put(item)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            for _ in range(num_threads):
                executor.submit(self._worker)

        logger.info(f"Prepare complete. {self.results.items_processed} {self.entity} processed.")
        return self.results

    def _worker(self):
        while True:
            try:
                item = self.work_queue.get_nowait()
                self._process_item(item)
                self.work_queue.task_done()
            except queue.Empty:
                break

    def _get_items(self, limit: Optional[int]) -> List[Dict[str, Any]]:
        raise NotImplementedError("Subclasses must implement this method")

    def _process_item(self, item: Dict[str, Any]):
        raise NotImplementedError("Subclasses must implement this method")

    def _generate_chunks(self, text: str) -> List[str]:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=4000,
            chunk_overlap=400,
            length_function=len,
        )
        return text_splitter.split_text(text)

    def _generate_embeddings(self, chunks: List[str]) -> List[List[float]]:
        return self.embeddings.embed_documents(chunks)

    def upload(self, index_name: str = "") -> ProcessorResult:
        result = ProcessorResult(action="upload", entity=self.entity)
        
        pc = Pinecone()
        if index_name == "":
            index_name = os.getenv("PINECONE_INDEX")
        index = pc.Index(index_name)

        embeddings_to_upload = self._read_filtered_embeddings()
        
        logger.info(f"Total {self.entity} embeddings to upload: {len(embeddings_to_upload)}")

        batch_size = 100
        for i in range(0, len(embeddings_to_upload), batch_size):
            batch = embeddings_to_upload[i:i+batch_size]
            self._upsert_batch(index, batch)
            result.items_processed += len(batch)
            logger.info(f"Uploaded {result.items_processed} {self.entity} embeddings so far...")

        self._move_processed_files()

        logger.info(f"Upload complete. {result.items_processed} {self.entity} embeddings uploaded.")
        return result

    def _read_filtered_embeddings(self) -> List[AutobotEmbedding]:
        embeddings = []
        for filename in os.listdir(self.output_dir):
            if filename.endswith("_embeddings.json"):
                file_path = os.path.join(self.output_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_embeddings = json.load(f)
                    filtered_embeddings = [
                        AutobotEmbedding.from_dict(e) for e in file_embeddings
                        if e['company'] == self.company and e['model_name'] == self.model_name and e['dimensions'] == self.dimensions
                    ]
                    embeddings.extend(filtered_embeddings)
        return embeddings

    def _upsert_batch(self, index, batch: List[AutobotEmbedding]):
        vectors = [
            (
                str(hash(e.chunk)),
                e.embedding,
                {**e.metadata, "chunk": e.chunk}
            ) for e in batch
        ]
        index.upsert(vectors=vectors)

    def _move_processed_files(self):
        for filename in os.listdir(self.output_dir):
            if f"{self.entity}" in filename and filename.endswith("_embeddings.json"):
                src = os.path.join(self.output_dir, filename)
                dst = os.path.join(self.uploaded_dir, filename)
                os.rename(src, dst)
                logger.info(f"Moved {filename} to uploaded_embeddings directory")



