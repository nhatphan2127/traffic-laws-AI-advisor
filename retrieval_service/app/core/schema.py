from dataclasses import dataclass, asdict
from typing import Any, Optional

from pydantic import BaseModel, Field


@dataclass
class RetrievalDocument:
    id: str
    total_score: float
    sparse_score: float
    dense_score: float
    text: str
    metadata: dict[str, Any]


class RetrievedChunk(BaseModel):
    """Wire format of a retrieved chunk, shared by the REST API and the MCP tools."""

    id: str
    total_score: float = 0.0
    dense_score: Optional[float] = 0.0
    sparse_score: Optional[float] = 0.0
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_document(cls, doc: RetrievalDocument) -> "RetrievedChunk":
        return cls(**asdict(doc))
