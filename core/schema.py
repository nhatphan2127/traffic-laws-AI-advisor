from dataclasses import dataclass
from typing import Any, Dict

@dataclass
class RetrievalDocument:
    id: str
    total_score: float
    sparse_score:float
    dense_score:float
    text: str
    metadata: dict[str, Any]