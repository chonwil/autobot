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
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            chunk=data['chunk'],
            embedding=data['embedding'],
            metadata=data['metadata'],
            company=data['company'],
            model_name=data['model_name'],
            dimensions=data['dimensions']
        )