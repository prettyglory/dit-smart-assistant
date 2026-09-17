import hashlib
import json
from pathlib import Path

from pypdf import PdfReader

from app.services.vector_store import (
    reset_collection,
    upsert_chunks,
)


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent

KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "knowledge_base"


def parse_txt_document(file_path: Path):
    metadata = {
        "source_title": file_path.stem,
        "source_url": "",
        "campus": "unknown",
        "category": "general",
        "level": "general",
        "file": file_path.name,
        "document_type": "txt",
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


def load_pdf_metadata(file_path: Path):
    metadata = {
        "source_title": file_path.stem.replace("_", " "),
        "source_url": "",
        "campus": "all",
        "category": "general",
        "level": "general",
        "file": file_path.name,
        "document_type": "pdf",
    }

    metadata_file = file_path.with_suffix(
        ".meta.json"
    )

    if metadata_file.exists():

        try:
            custom_metadata = json.loads(
                metadata_file.read_text(
                    encoding="utf-8"
                )
            )

            metadata.update(
                custom_metadata
            )

        except Exception as error:
            print(
                f"Warning: Could not read metadata "
                f"for {file_path.name}: {error}"
            )

    return metadata


def extract_pdf_pages(file_path: Path):
    reader = PdfReader(
        str(file_path)
    )

    pages = []

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):

        try:
            text = page.extract_text(
                extraction_mode="layout"
            )

        except Exception:
            text = page.extract_text()

        if text:
            text = text.strip()

        if not text:
            print(
                f"Warning: No text extracted from "
                f"{file_path.name}, page {page_number}"
            )
            continue

        pages.append(
            {
                "page": page_number,
                "text": text,
            }
        )

    return pages


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

        chunk = " ".join(
            chunk_words
        ).strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(words):
            break

        start += (
            chunk_size - overlap
        )

    return chunks


def generate_id(
    file_path: Path,
    index: int,
    page: int = 0,
):
    raw_id = (
        f"{file_path}-{page}-{index}"
    )

    return hashlib.sha1(
        raw_id.encode("utf-8")
    ).hexdigest()


def ingest_txt_file(
    file_path: Path,
    documents: list,
    metadatas: list,
    ids: list,
):
    content, metadata = (
        parse_txt_document(
            file_path
        )
    )

    if not content:
        print(
            f"Skipped empty TXT file: "
            f"{file_path.name}"
        )
        return

    chunks = chunk_text(
        content
    )

    relative_path = (
        file_path.relative_to(
            KNOWLEDGE_BASE_DIR
        )
    )

    for index, chunk in enumerate(
        chunks
    ):

        chunk_metadata = (
            metadata.copy()
        )

        chunk_metadata["path"] = str(
            relative_path
        )

        chunk_metadata["chunk"] = (
            index
        )

        chunk_metadata["page"] = 0

        documents.append(
            chunk
        )

        metadatas.append(
            chunk_metadata
        )

        ids.append(
            generate_id(
                relative_path,
                index,
            )
        )


def ingest_pdf_file(
    file_path: Path,
    documents: list,
    metadatas: list,
    ids: list,
):
    metadata = load_pdf_metadata(
        file_path
    )

    pages = extract_pdf_pages(
        file_path
    )

    relative_path = (
        file_path.relative_to(
            KNOWLEDGE_BASE_DIR
        )
    )

    total_chunks = 0

    for page_data in pages:

        page_number = (
            page_data["page"]
        )

        page_text = (
            page_data["text"]
        )

        chunks = chunk_text(
            page_text
        )

        for index, chunk in enumerate(
            chunks
        ):

            chunk_metadata = (
                metadata.copy()
            )

            chunk_metadata["path"] = str(
                relative_path
            )

            chunk_metadata["page"] = (
                page_number
            )

            chunk_metadata["chunk"] = (
                index
            )

            documents.append(
                chunk
            )

            metadatas.append(
                chunk_metadata
            )

            ids.append(
                generate_id(
                    relative_path,
                    index,
                    page_number,
                )
            )

            total_chunks += 1

    print(
        f"Extracted {len(pages)} pages "
        f"and {total_chunks} chunks "
        f"from {file_path.name}"
    )


def ingest():

    if not KNOWLEDGE_BASE_DIR.exists():
        raise FileNotFoundError(
            f"Knowledge base directory "
            f"not found: "
            f"{KNOWLEDGE_BASE_DIR}"
        )

    reset_collection()

    documents = []
    metadatas = []
    ids = []

    txt_files = list(
        KNOWLEDGE_BASE_DIR.rglob(
            "*.txt"
        )
    )

    pdf_files = list(
        KNOWLEDGE_BASE_DIR.rglob(
            "*.pdf"
        )
    )

    # Do not ingest metadata text files
    txt_files = [
        file_path
        for file_path in txt_files
        if not file_path.name.endswith(
            ".meta.txt"
        )
    ]

    print(
        f"Found {len(txt_files)} "
        f"TXT knowledge files."
    )

    print(
        f"Found {len(pdf_files)} "
        f"PDF knowledge files."
    )

    print()

    for file_path in txt_files:

        relative_path = (
            file_path.relative_to(
                KNOWLEDGE_BASE_DIR
            )
        )

        print(
            f"Processing TXT: "
            f"{relative_path}"
        )

        ingest_txt_file(
            file_path,
            documents,
            metadatas,
            ids,
        )

    for file_path in pdf_files:

        relative_path = (
            file_path.relative_to(
                KNOWLEDGE_BASE_DIR
            )
        )

        print(
            f"Processing PDF: "
            f"{relative_path}"
        )

        ingest_pdf_file(
            file_path,
            documents,
            metadatas,
            ids,
        )

    upsert_chunks(
        documents=documents,
        metadatas=metadatas,
        ids=ids,
    )

    print()
    print(
        f"Ingested {len(documents)} "
        f"total chunks into ChromaDB."
    )


if __name__ == "__main__":
    ingest()