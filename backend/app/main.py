from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import ALLOWED_ORIGINS
from app.schemas import ChatRequest, ChatResponse
from app.services.agent_service import run_dit_agent
from app.services.session_memory import session_memory


app = FastAPI(
    title="DIT Smart Assistant API",
    version="2.1.0",
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
    session_id = session_memory.resolve_session_id(
        request.session_id
    )

    client_history = [
        message.model_dump()
        for message in request.history
    ]

    session_memory.seed_history(
        session_id=session_id,
        history=client_history,
    )

    history = session_memory.get_history(
        session_id
    )

    answer, sources = run_dit_agent(
        question=request.message,
        history=history,
    )

    session_memory.append_turn(
        session_id=session_id,
        user_message=request.message,
        assistant_message=answer,
    )

    return ChatResponse(
        answer=answer,
        sources=sources,
        session_id=session_id,
    )


@app.delete("/api/sessions/{session_id}")
def clear_session(session_id: str):
    cleared = session_memory.clear(
        session_id
    )

    return {
        "status": "cleared" if cleared else "not_found",
        "session_id": session_id,
    }
