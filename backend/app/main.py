from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import ALLOWED_ORIGINS
from app.schemas import ChatRequest, ChatResponse
from app.services.rag_service import answer_with_rag


app = FastAPI(
    title="DIT Smart Assistant API",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "DIT Smart Assistant API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.post(
    "/api/chat",
    response_model=ChatResponse,
)
def chat(request: ChatRequest):

    history = [
        message.model_dump()
        for message in request.history
    ]

    answer, sources = answer_with_rag(
        question=request.message,
        history=history,
    )

    return ChatResponse(
        answer=answer,
        sources=sources,
    )