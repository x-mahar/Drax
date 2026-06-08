# api/models.py

from pydantic import BaseModel
from typing import Any


class QueryRequest(BaseModel):
    question: str


class ChartConfig(BaseModel):
    type: str        # bar | line | pie | scatter | horizontal_bar
    title: str
    x_key: str
    y_key: str
    x_label: str
    y_label: str


class QueryResponse(BaseModel):
    status: str                      # success | error
    question: str
    db_type: str
    sql: str | None                  # None for Mongo/Redis/Chroma
    answer: str
    key_insights: list[str]
    charts: list[ChartConfig]
    data: list[dict[str, Any]]
    row_count: int
    self_healed: bool
    message: str | None              # error message if status == error