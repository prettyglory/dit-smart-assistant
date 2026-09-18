from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str

    history: list[ChatMessage] = Field(
        default_factory=list
    )


class Source(BaseModel):
    title: str
    url: str = ""
    campus: str = ""
    page: int | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]