import argparse
import logging
from pathlib import Path
import sys, os
# Add the project root to PYTHONPATH for direct script runs
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.services.retriever import retrieve

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_top_chunks(query: str, top_k: int = settings.top_k) -> list[dict]:
    """Retrieve the top‑k chunks for *query* using the existing retriever.

    Returns a list of dictionaries, each containing at least:
        - ``source_file``
        - ``doc_id`` (if present)
        - ``chunk_id``
        - ``text`` (excerpt)
        - ``score`` (similarity score returned by the vector store)
    """
    chunks = retrieve(query, top_k=top_k)
    # Ensure a stable order for reproducibility – sort by descending score.
    sorted_chunks = sorted(chunks, key=lambda c: float(c.get("score", 0.0)), reverse=True)
    return sorted_chunks

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Debug helper: show the top‑k retrieved chunks for a query."
    )
    parser.add_argument("query", help="The question or query to retrieve chunks for.")
    parser.add_argument(
        "-k",
        "--top",
        type=int,
        default=settings.top_k,
        help="Number of chunks to retrieve (default: settings.top_k).",
    )
    args = parser.parse_args()

    logger.info("Fetching top %d chunks for query: %s", args.top, args.query)
    chunks = get_top_chunks(args.query, top_k=args.top)

    if not chunks:
        print("No chunks were retrieved. Check that the vector store exists and contains data.")
        return

    for i, chunk in enumerate(chunks, start=1):
        source = chunk.get("source_file", "<unknown>")
        doc_id = chunk.get("doc_id", "<none>")
        chunk_id = chunk.get("chunk_id", "<none>")
        score = chunk.get("score", "0")
        text = chunk.get("text", "").strip().replace("\n", " ")
        preview = text[:200] + ("…" if len(text) > 200 else "")
        print(f"--- Chunk {i} ---")
        print(f"Source file : {source}")
        print(f"Doc ID      : {doc_id}")
        print(f"Chunk ID    : {chunk_id}")
        print(f"Score       : {score}")
        print(f"Preview     : {preview}\n")

if __name__ == "__main__":
    main()
