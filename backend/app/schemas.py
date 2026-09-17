from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


class Source(BaseModel):
    title: str
    url: str = ""
    campus: str = ""


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]