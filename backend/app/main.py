from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import ChatRequest, ChatResponse
from app.services.groq_service import ask_groq


app = FastAPI(
    title="DIT Smart Assistant API",
    description="AI-powered information assistant for DIT",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "DIT Smart Assistant API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    answer = ask_groq(request.message)

    return ChatResponse(
        answer=answer
    )