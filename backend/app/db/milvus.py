from __future__ import annotations

from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility

from app.core.config import settings

COLLECTION_NAME = "paper_chunks"
EMBEDDING_DIM = 1536

_collection: Collection | None = None


def _ensure_collection() -> Collection:
    if not utility.has_collection(COLLECTION_NAME):
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="paper_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="section_idx", dtype=DataType.INT32),
            FieldSchema(name="chunk_text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
        ]
        schema = CollectionSchema(fields, description="Paper text chunks with embeddings")
        col = Collection(COLLECTION_NAME, schema)
        index_params = {
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128},
        }
        col.create_index("embedding", index_params)
    else:
        col = Collection(COLLECTION_NAME)
    col.load()
    return col


def init_milvus() -> None:
    global _collection
    connections.connect(alias="default", host=settings.milvus_host, port=settings.milvus_port)
    _collection = _ensure_collection()


def close_milvus() -> None:
    global _collection
    if _collection is not None:
        _collection.release()
        _collection = None
    connections.disconnect(alias="default")


def get_collection() -> Collection:
    if _collection is None:
        raise RuntimeError("Milvus not initialised – call init_milvus() first")
    return _collection


def insert_chunks(paper_id: str, chunks: list[dict]) -> None:
    """Insert paper chunks into Milvus.

    Each chunk dict must contain: section_idx (int), chunk_text (str), embedding (list[float]).
    """
    col = get_collection()
    data = [
        [c["paper_id"] if "paper_id" in c else paper_id for c in chunks],
        [c["section_idx"] for c in chunks],
        [c["chunk_text"] for c in chunks],
        [c["embedding"] for c in chunks],
    ]
    col.insert(data)
    col.flush()


def search_chunks(query_embedding: list[float], paper_id: str | None = None, top_k: int = 5) -> list[dict]:
    col = get_collection()
    search_params = {"metric_type": "COSINE", "params": {"nprobe": 16}}
    expr = f'paper_id == "{paper_id}"' if paper_id else None
    results = col.search(
        data=[query_embedding],
        anns_field="embedding",
        param=search_params,
        limit=top_k,
        expr=expr,
        output_fields=["paper_id", "section_idx", "chunk_text"],
    )
    hits = []
    for hit in results[0]:
        hits.append({
            "id": hit.id,
            "score": hit.score,
            "paper_id": hit.entity.get("paper_id"),
            "section_idx": hit.entity.get("section_idx"),
            "chunk_text": hit.entity.get("chunk_text"),
        })
    return hits


def delete_paper_chunks(paper_id: str) -> None:
    col = get_collection()
    col.delete(expr=f'paper_id == "{paper_id}"')
    col.flush()
