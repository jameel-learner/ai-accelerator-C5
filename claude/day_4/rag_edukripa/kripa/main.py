"""
Run this to index PDFs:
    python src/main.py                  # indexes every PDF in data/
    python src/main.py data/one.pdf     # indexes just that file

Then chat with it via:
    python src/rag.py
or the web UI:
    streamlit run src/app.py
"""

import os
import sys
from pdf_parser import extract_pages
from chunker import chunk_text
from vector_store import VectorStore


def index_pdf(pdf_path: str, store: VectorStore = None) -> VectorStore:
    store = store or VectorStore()
    source = os.path.basename(pdf_path)

    print(f"Indexing: {pdf_path}\n")

    pages = extract_pages(pdf_path)
    chunks = chunk_text(pages, source=source, chunk_size=300, overlap=50)
    store.add_chunks(chunks)

    return store


def index_all(data_dir: str = "data", store: VectorStore = None) -> VectorStore:
    store = store or VectorStore()
    pdf_paths = sorted(
        os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.lower().endswith(".pdf")
    )

    if not pdf_paths:
        print(f"No PDFs found in {data_dir}/")
        return store

    for pdf_path in pdf_paths:
        index_pdf(pdf_path, store=store)

    return store


if __name__ == "__main__":
    if len(sys.argv) == 1:
        index_all()
    elif len(sys.argv) == 2:
        index_pdf(sys.argv[1])
    else:
        print("Usage: python src/main.py [path_to_pdf]")
        sys.exit(1)

    print("\nDone. Now run: python src/rag.py (or: streamlit run src/app.py)")
