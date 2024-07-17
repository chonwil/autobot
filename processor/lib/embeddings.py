from typing import List, Dict, Any
from dataclasses import dataclass, asdict

@dataclass
class ArticleSectionEmbedding:
    chunk: str
    embedding: List[float]
    metadata: Dict[str, Any]
    company: str
    model_name: str
    dimensions: int

    def to_dict(self):
        return asdict(self)