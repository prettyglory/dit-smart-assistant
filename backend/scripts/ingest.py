import hashlib
from pathlib import Path

from app.services.vector_store import (
    reset_collection,
    upsert_chunks,
)


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent

KNOWLEDGE_BASE_DIR = (
    PROJECT_ROOT / "knowledge_base"
)


def parse_document(file_path: Path):

    metadata = {
        "source_title": file_path.stem,
        "source_url": "",
        "campus": "unknown",
        "file": str(file_path.name),
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

        chunk = " ".join(chunk_words)

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
        raw_id.encode()
    ).hexdigest()


def ingest():

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

        content, metadata = parse_document(
            file_path
        )

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

            metadatas.append(
                chunk_metadata
            )

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

    print(
        f"Ingested {len(documents)} chunks "
        "into ChromaDB."
    )


if __name__ == "__main__":
    ingest()