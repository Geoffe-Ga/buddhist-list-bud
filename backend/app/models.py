from pydantic import BaseModel


class NodeSummary(BaseModel):
    id: str
    name: str
    type: str | None = None


class CurrentNode(BaseModel):
    id: str
    type: str
    name: str
    pali_name: str
    essay: str | None = None
    description: str | None = None


class NavigateResponse(BaseModel):
    current: CurrentNode
    up: NodeSummary | None = None
    down: NodeSummary | None = None
    left: list[NodeSummary] = []
    right: list[NodeSummary] = []
    breadcrumbs: list[NodeSummary] = []


class ListSummary(BaseModel):
    id: str
    name: str
    pali_name: str
    slug: str
    item_count: int


class SearchResult(BaseModel):
    id: str
    name: str
    pali_name: str
    type: str
