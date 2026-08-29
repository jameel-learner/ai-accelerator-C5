"""
Wraps ChromaDB (a local, file-based vector database) with sentence-transformers
embeddings (runs on your CPU, no API cost).

Chroma persists to disk in `persist_dir`, so you only need to embed your PDF
once. Re-running the script later will reuse the existing collection unless
you delete the folder or call reset().
"""

import chromadb
from chromadb.utils import embedding_functions


class VectorStore:
    def __init__(self, persist_dir: str = "./chroma_db", collection_name: str = "pdf_chunks"):
        self.client = chromadb.PersistentClient(path=persist_dir)

        # all-MiniLM-L6-v2 is small (~80MB), fast on CPU, and good enough to start with.
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        # Explicit cosine space (Chroma's default is squared L2) so distance
        # lands in a well-defined [0, 2] range - that's what lets us turn it
        # into a bounded confidence score (see query_with_candidates below).
        # NOTE: a collection's distance space is fixed at creation, so
        # switching this requires deleting persist_dir and re-indexing.
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

    def list_sources(self) -> set[str]:
        """Returns the set of distinct source filenames already indexed."""
        metadatas = self.collection.get()["metadatas"]
        return {m["source"] for m in metadatas}

    def add_chunks(self, chunks: list[dict]):
        """
        chunks: output of chunker.chunk_text(), all from the same source file.
        Adds them to the collection. Chroma handles embedding internally
        using the embedding_fn we configured above.

        Skips (per-source) if this source's chunks are already indexed, so
        multiple documents can share one collection without re-adding on
        every run.
        """
        source = chunks[0]["source"]
        if source in self.list_sources():
            print(f"'{source}' is already indexed. Skipping "
                  f"(delete the persist_dir folder if you want to re-index from scratch).")
            return

        self.collection.add(
            ids=[f"{c['source']}::{c['chunk_id']}" for c in chunks],
            documents=[c["text"] for c in chunks],
            metadatas=[
                {
                    "page": c["page"],
                    "source": c["source"],
                    "chunk_id": c["chunk_id"],
                    "word_start": c["word_start"],
                    "word_end": c["word_end"],
                    "chunk_size": c["chunk_size"],
                    "overlap": c["overlap"],
                }
                for c in chunks
            ],
        )
        print(f"Added {len(chunks)} chunks from '{source}' to the vector store.")

    def query(self, question: str, top_k: int = 5, sources: list[str] | None = None) -> list[dict]:
        """
        Returns the top_k most relevant chunks for the question, as
        [{"text": ..., "page": ..., "source": ..., "distance": ...}, ...]
        Lower distance = more similar.

        sources: if given, restrict the search to chunks from just these
        filenames (an empty list matches nothing). None = search everything.
        """
        if sources is not None and len(sources) == 0:
            return []  # Chroma rejects an empty $in list, so short-circuit here

        where = {"source": {"$in": sources}} if sources is not None else None
        results = self.collection.query(query_texts=[question], n_results=top_k, where=where)

        retrieved = []
        for text, meta, dist in zip(
            results["documents"][0], results["metadatas"][0], results["distances"][0]
        ):
            retrieved.append({
                "text": text,
                "page": meta["page"],
                "source": meta["source"],
                "distance": dist,
            })
        return retrieved

    def query_with_candidates(
        self, question: str, top_k: int = 5, fetch_k: int | None = None,
        sources: list[str] | None = None,
    ) -> tuple[list[dict], list[dict]]:
        """
        Like query(), but also fetches extra lower-ranked candidates purely
        for observability - so the dashboard can show what was retrieved
        but NOT used, not just the top_k chunks that made it into the
        prompt. Also computes a "confidence" per chunk (1 - distance / 2,
        which lands in [0, 1] since the collection uses cosine space).

        Returns (kept, discarded): kept is the top_k chunks actually used
        (what search_documents sends to the LLM), discarded is the extra
        fetch_k - top_k candidates that were fetched but cut by rank.
        """
        fetch_k = max(fetch_k or top_k, top_k)
        if sources is not None and len(sources) == 0:
            return [], []

        where = {"source": {"$in": sources}} if sources is not None else None
        results = self.collection.query(query_texts=[question], n_results=fetch_k, where=where)

        if not results["documents"][0]:
            return [], []

        candidates = []
        for rank, (text, meta, dist) in enumerate(
            zip(results["documents"][0], results["metadatas"][0], results["distances"][0]), start=1
        ):
            candidates.append({
                "text": text,
                "page": meta["page"],
                "source": meta["source"],
                "chunk_id": meta.get("chunk_id"),
                "distance": dist,
                "confidence": 1 - (dist / 2),
                "rank": rank,
                "kept": rank <= top_k,
            })

        kept = [c for c in candidates if c["kept"]]
        discarded = [c for c in candidates if not c["kept"]]
        return kept, discarded

    def get_chunk_metadata(self, source: str, chunk_id: int) -> dict | None:
        """Looks up one chunk's full stored metadata (incl. chunking boundaries) by id."""
        result = self.collection.get(ids=[f"{source}::{chunk_id}"], include=["metadatas", "documents"])
        if not result["ids"]:
            return None
        return {"text": result["documents"][0], **result["metadatas"][0]}

    def all_chunks(self) -> list[dict]:
        """Returns every stored chunk's metadata + text - used by the stored-data browser."""
        result = self.collection.get(include=["metadatas", "documents"])
        return [{"text": doc, **meta} for doc, meta in zip(result["documents"], result["metadatas"])]
