import os
import subprocess
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv


# =========================================================
# PATHS
# =========================================================

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
CHROMA_DIR = BACKEND_DIR / "chroma_db"
LOCAL_ENV_FILE = BACKEND_DIR / ".env"

# Make backend/app importable as "app"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="DIT Smart Assistant",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="auto",
)


# =========================================================
# LOAD GROQ KEY
# =========================================================

# Local development
if LOCAL_ENV_FILE.exists():
    load_dotenv(LOCAL_ENV_FILE)


# Streamlit Cloud secrets
if not os.getenv("GROQ_API_KEY"):
    try:
        streamlit_groq_key = st.secrets["GROQ_API_KEY"]
        os.environ["GROQ_API_KEY"] = streamlit_groq_key
    except Exception:
        pass


if not os.getenv("GROQ_API_KEY"):
    st.error("GROQ_API_KEY is not configured.")
    st.info(
        "Add GROQ_API_KEY to Streamlit Secrets "
        "or backend/.env for local development."
    )
    st.stop()


# =========================================================
# BUILD / LOAD CHROMA DATABASE
# =========================================================

@st.cache_resource(show_spinner=False)
def prepare_knowledge_base():
    """
    Create ChromaDB if no local vector database exists.
    """

    database_exists = (
        CHROMA_DIR.exists()
        and any(CHROMA_DIR.iterdir())
    )

    if database_exists:
        return True

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.ingest",
        ],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        st.error(
            "Could not prepare the DIT knowledge base."
        )

        with st.expander("View ingestion error"):
            st.code(
                result.stderr
                or result.stdout
                or "Unknown ingestion error."
            )

        st.stop()

    return True


with st.spinner(
    "Preparing verified DIT knowledge..."
):
    prepare_knowledge_base()


# Import the agent only after Chroma has been prepared.
from app.services.agent_service import run_dit_agent


# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown(
    """
<style>
    .block-container {
        max-width: 900px;
        padding-top: 1.2rem;
        padding-bottom: 6rem;
    }

    .dit-header {
        text-align: center;
        margin-top: 0.4rem;
        margin-bottom: 1.3rem;
    }

    .dit-title {
        color: #143a78;
        font-size: 2rem;
        font-weight: 750;
        line-height: 1.2;
        margin-bottom: 0.3rem;
    }

    .dit-subtitle {
        color: #4b5563;
        font-size: 1rem;
        margin-bottom: 0.45rem;
    }

    .iso-badge {
        display: inline-block;
        padding: 0.28rem 0.7rem;
        border-radius: 999px;
        background: #edf4ff;
        color: #143a78;
        border: 1px solid #dbeafe;
        font-size: 0.76rem;
        font-weight: 650;
    }

    div[data-testid="stChatMessage"] {
        border-radius: 14px;
    }

    div[data-testid="stChatInput"] {
        border-radius: 15px;
    }

    .stButton > button {
        border-radius: 10px;
    }

    [data-testid="stSidebar"] {
        border-right: 1px solid #e5e7eb;
    }

    .dit-note {
        color: #6b7280;
        font-size: 0.86rem;
        text-align: center;
        margin-bottom: 1rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# HEADER
# =========================================================

logo_path = (
    ROOT_DIR
    / "frontend"
    / "public"
    / "dit-logo.png"
)


# Center logo
if logo_path.exists():
    left, center, right = st.columns(
        [3, 1, 3]
    )

    with center:
        st.image(
            str(logo_path),
            width=85,
        )


# IMPORTANT:
# HTML starts directly at the beginning of the string.
# This prevents Markdown from rendering it as a code block.
st.markdown(
    """<div class="dit-header">
<div class="dit-title">DIT Smart Assistant</div>
<div class="dit-subtitle">Dar es Salaam Institute of Technology</div>
<div class="iso-badge">ISO 21001:2018 Certified</div>
</div>""",
    unsafe_allow_html=True,
)


st.markdown(
    """<div class="dit-note">
Ask verified DIT questions in English or Kiswahili.
</div>""",
    unsafe_allow_html=True,
)


# =========================================================
# INITIAL MESSAGE
# =========================================================

INITIAL_MESSAGE = {
    "role": "assistant",
    "content": (
        "Hello! Karibu **DIT Smart Assistant** 👋\n\n"
        "You can ask about DIT **campuses, programmes, "
        "admissions, fees, accommodation, regulations, "
        "IPT and academic information**.\n\n"
        "Unaweza kuuliza kwa **English au Kiswahili**."
    ),
    "sources": [],
}


if "messages" not in st.session_state:
    st.session_state.messages = [
        INITIAL_MESSAGE
    ]


if "feedback" not in st.session_state:
    st.session_state.feedback = {}


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:
    st.title("DIT Smart Assistant")

    st.caption(
        "Agentic AI with verified DIT knowledge"
    )

    st.divider()

    st.markdown("**Suggested questions**")

    suggestions = [
        "DIT ina campuses ngapi?",
        "What programmes does DIT offer?",
        "What are the requirements for joining DIT?",
        "How much is Bachelor tuition fee?",
        "Who gets priority for hostel accommodation?",
    ]

    selected_suggestion = None

    for suggestion in suggestions:
        if st.button(
            suggestion,
            use_container_width=True,
            key=f"suggestion_{suggestion}",
        ):
            selected_suggestion = suggestion

    st.divider()

    if st.button(
        "🗑️ Clear Chat",
        use_container_width=True,
    ):
        st.session_state.messages = [
            INITIAL_MESSAGE
        ]

        st.session_state.feedback = {}

        st.rerun()


# =========================================================
# SOURCE RENDERER
# =========================================================

def normalize_source(source):
    """
    Support either dictionaries or Pydantic-style
    source objects.
    """

    if isinstance(source, dict):
        return source

    if hasattr(source, "model_dump"):
        return source.model_dump()

    return {
        "title": getattr(
            source,
            "title",
            "DIT Source",
        ),
        "url": getattr(
            source,
            "url",
            "",
        ),
        "page": getattr(
            source,
            "page",
            None,
        ),
        "campus": getattr(
            source,
            "campus",
            "",
        ),
    }


def render_sources(sources):
    if not sources:
        return

    with st.expander(
        "📚 Verified Sources"
    ):
        for source_item in sources:
            source = normalize_source(
                source_item
            )

            title = source.get(
                "title",
                "DIT Source",
            )

            url = source.get(
                "url",
                "",
            )

            page = source.get(
                "page"
            )

            campus = source.get(
                "campus",
                "",
            )

            if url:
                st.markdown(
                    f"**[{title}]({url})**"
                )
            else:
                st.markdown(
                    f"**{title}**"
                )

            metadata_parts = []

            if page is not None:
                metadata_parts.append(
                    f"Page {page}"
                )

            if (
                campus
                and campus.lower()
                != "unknown"
            ):
                if campus.lower() == "all":
                    metadata_parts.append(
                        "All campuses"
                    )
                else:
                    metadata_parts.append(
                        f"{campus} Campus"
                    )

            if metadata_parts:
                st.caption(
                    " • ".join(
                        metadata_parts
                    )
                )

            st.divider()


# =========================================================
# DISPLAY CHAT HISTORY
# =========================================================

for index, message in enumerate(
    st.session_state.messages
):
    with st.chat_message(
        message["role"]
    ):
        st.markdown(
            message["content"]
        )

        if message["role"] == "assistant":
            render_sources(
                message.get(
                    "sources",
                    [],
                )
            )

            if index != 0:
                col1, col2, col3 = st.columns(
                    [1, 1, 8]
                )

                with col1:
                    if st.button(
                        "👍",
                        key=f"up_{index}",
                        help="Helpful",
                    ):
                        st.session_state.feedback[
                            index
                        ] = "positive"

                with col2:
                    if st.button(
                        "👎",
                        key=f"down_{index}",
                        help="Not helpful",
                    ):
                        st.session_state.feedback[
                            index
                        ] = "negative"

                with col3:
                    if index in st.session_state.feedback:
                        st.caption(
                            "Thanks for your feedback."
                        )


# =========================================================
# CHAT INPUT
# =========================================================

typed_question = st.chat_input(
    "Ask anything about DIT..."
)


question = (
    selected_suggestion
    or typed_question
)


# =========================================================
# HANDLE QUESTION
# =========================================================

if question:
    question = question.strip()

    if question:
        # Build history BEFORE inserting
        # the current user question.
        history = []

        for message in (
            st.session_state.messages[-6:]
        ):
            history.append(
                {
                    "role": message["role"],
                    "content": message[
                        "content"
                    ],
                }
            )

        user_message = {
            "role": "user",
            "content": question,
            "sources": [],
        }

        st.session_state.messages.append(
            user_message
        )

        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner(
                "Thinking and searching verified DIT information..."
            ):
                try:
                    answer, sources = (
                        run_dit_agent(
                            question=question,
                            history=history,
                        )
                    )

                    st.markdown(answer)

                    render_sources(
                        sources
                    )

                    assistant_message = {
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                    }

                    st.session_state.messages.append(
                        assistant_message
                    )

                except Exception as error:
                    error_message = (
                        "Sorry, I could not process "
                        "that question. Please try again."
                    )

                    st.error(
                        error_message
                    )

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": error_message,
                            "sources": [],
                        }
                    )

                    with st.expander(
                        "Technical details"
                    ):
                        st.code(
                            str(error)
                        )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "DIT Smart Assistant provides information from "
    "available verified DIT sources. For official "
    "decisions, confirm critical information through "
    "the relevant DIT office or official DIT website."
)
