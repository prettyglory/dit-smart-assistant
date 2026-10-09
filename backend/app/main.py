from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import ALLOWED_ORIGINS
from app.schemas import ChatRequest, ChatResponse
from app.services.execution_trace import agent_traces
from app.services.session_memory import session_memory
from app.services.traced_agent_service import run_traced_dit_agent


app = FastAPI(
    title="DIT Smart Assistant API",
    version="2.3.0",
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

    student_state = session_memory.update_student_state_from_message(
        session_id=session_id,
        message=request.message,
    )

    history = session_memory.get_history(
        session_id
    )

    answer, sources, trace_id = run_traced_dit_agent(
        question=request.message,
        history=history,
        student_state=student_state,
        session_id=session_id,
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
        trace_id=trace_id,
    )


@app.get("/api/traces/{trace_id}")
def get_agent_trace(trace_id: str):
    trace = agent_traces.get(
        trace_id
    )

    if trace is None:
        raise HTTPException(
            status_code=404,
            detail="Agent execution trace not found or expired.",
        )

    return trace


@app.delete("/api/sessions/{session_id}")
def clear_session(session_id: str):
    cleared = session_memory.clear(
        session_id
    )

    return {
        "status": "cleared" if cleared else "not_found",
        "session_id": session_id,
    }
