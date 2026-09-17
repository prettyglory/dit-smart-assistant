from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


class Source(BaseModel):
    title: str
    url: str = ""
    campus: str = ""
    page: int | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]