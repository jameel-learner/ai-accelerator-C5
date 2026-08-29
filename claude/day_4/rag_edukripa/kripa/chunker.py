"""
Splits extracted page text into overlapping chunks suitable for embedding.

Why overlap? If a sentence or idea gets cut at a chunk boundary, overlap
means it's likely to appear whole in at least one chunk. Without it,
you can lose the exact fact you needed right at a chunk edge.

We chunk by word count as a simple, dependency-free approximation of
token count (roughly 0.75 words per token for English, but word count
alone is good enough to start with).
"""


def chunk_text(pages: list[dict], source: str, chunk_size: int = 300, overlap: int = 50) -> list[dict]:
    """
    pages: output of pdf_parser.extract_pages()
    source: filename the pages came from (stamped onto every chunk so
        retrieval can cite which document an answer came from)
    chunk_size: target number of words per chunk
    overlap: number of words repeated between consecutive chunks

    Returns a list of {"text": str, "page": int, "chunk_id": int, "source": str,
    "word_start": int, "word_end": int, "chunk_size": int, "overlap": int} dicts.
    word_start/word_end are the word-index boundaries within that page's text,
    and chunk_size/overlap record the params this chunk was produced with -
    kept for observability so the dashboard can show exactly how a document
    was split without recomputing it.
    """
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks = []
    chunk_id = 0

    for page in pages:
        words = page["text"].split()
        start = 0

        while start < len(words):
            end = start + chunk_size
            chunk_words = words[start:end]
            chunk_str = " ".join(chunk_words)

            chunks.append({
                "text": chunk_str,
                "page": page["page"],
                "chunk_id": chunk_id,
                "source": source,
                "word_start": start,
                "word_end": min(end, len(words)),
                "chunk_size": chunk_size,
                "overlap": overlap,
            })
            chunk_id += 1

            if end >= len(words):
                break
            start = end - overlap  # step forward, but re-include the overlap

    print(f"Created {len(chunks)} chunks from {len(pages)} pages.")
    return chunks


if __name__ == "__main__":
    # quick manual test
    fake_pages = [{"page": 1, "text": " ".join(f"word{i}" for i in range(700))}]
    result = chunk_text(fake_pages, source="fake.pdf", chunk_size=300, overlap=50)
    for c in result:
        print(c["chunk_id"], c["page"], c["text"][:40], "...")
