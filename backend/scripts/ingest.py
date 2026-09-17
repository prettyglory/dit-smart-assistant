import hashlib
from pathlib import Path

from app.services.vector_store import (
    reset_collection,
    upsert_chunks,
)


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent

KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "knowledge_base"


def parse_document(file_path: Path):
    metadata = {
        "source_title": file_path.stem,
        "source_url": "",
        "campus": "unknown",
        "category": "general",
        "level": "general",
        "file": file_path.name,
    }

    content_lines = []

    text = file_path.read_text(
        encoding="utf-8"
    )

    for line in text.splitlines():

        stripped = line.strip()

        if stripped.startswith("SOURCE_TITLE:"):
            metadata["source_title"] = (
                stripped.split(":", 1)[1].strip()
            )

        elif stripped.startswith("SOURCE_URL:"):
            metadata["source_url"] = (
                stripped.split(":", 1)[1].strip()
            )

        elif stripped.startswith("CAMPUS:"):
            metadata["campus"] = (
                stripped.split(":", 1)[1].strip()
            )

        elif stripped.startswith("CATEGORY:"):
            metadata["category"] = (
                stripped.split(":", 1)[1].strip()
            )

        elif stripped.startswith("LEVEL:"):
            metadata["level"] = (
                stripped.split(":", 1)[1].strip()
            )

        else:
            content_lines.append(line)

    content = "\n".join(
        content_lines
    ).strip()

    return content, metadata


def chunk_text(
    text: str,
    chunk_size: int = 180,
    overlap: int = 30,
):
    words = text.split()

    chunks = []

    start = 0

    while start < len(words):

        end = start + chunk_size

        chunk_words = words[start:end]

        chunk = " ".join(chunk_words).strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(words):
            break

        start += chunk_size - overlap

    return chunks


def generate_id(
    file_path: Path,
    index: int,
):
    raw_id = f"{file_path}-{index}"

    return hashlib.sha1(
        raw_id.encode("utf-8")
    ).hexdigest()


def ingest():

    if not KNOWLEDGE_BASE_DIR.exists():
        raise FileNotFoundError(
            f"Knowledge base directory not found: "
            f"{KNOWLEDGE_BASE_DIR}"
        )

    reset_collection()

    documents = []
    metadatas = []
    ids = []

    files = list(
        KNOWLEDGE_BASE_DIR.rglob("*.txt")
    )

    print(
        f"Found {len(files)} knowledge files."
    )

    for file_path in files:

        print(
            f"Processing: "
            f"{file_path.relative_to(KNOWLEDGE_BASE_DIR)}"
        )

        content, metadata = parse_document(
            file_path
        )

        if not content:
            print(
                f"Skipped empty file: {file_path.name}"
            )
            continue

        chunks = chunk_text(content)

        for index, chunk in enumerate(chunks):

            chunk_metadata = metadata.copy()

            relative_path = file_path.relative_to(
                KNOWLEDGE_BASE_DIR
            )

            chunk_metadata["path"] = str(
                relative_path
            )

            chunk_metadata["chunk"] = index

            documents.append(chunk)
            metadatas.append(chunk_metadata)

            ids.append(
                generate_id(
                    relative_path,
                    index,
                )
            )

    upsert_chunks(
        documents=documents,
        metadatas=metadatas,
        ids=ids,
    )

    print()
    print(
        f"Ingested {len(documents)} chunks "
        "into ChromaDB."
    )


if __name__ == "__main__":
    ingest()