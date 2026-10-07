from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import ALLOWED_ORIGINS
from app.schemas import ChatRequest, ChatResponse
from app.services.agent_service import run_dit_agent


app = FastAPI(
    title="DIT Smart Assistant API",
    version="2.0.0",
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
        "message": "DIT Agentic AI Assistant API is running"
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

    answer, sources = run_dit_agent(
        question=request.message,
        history=history,
    )

    return ChatResponse(
        answer=answer,
        sources=sources,
    )
