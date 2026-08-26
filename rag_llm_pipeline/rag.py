import os
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer, CrossEncoder
from fastembed import SparseTextEmbedding


# ============================================================
# 1. Environment
# ============================================================

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

COLLECTION_NAME = "sprint_research"


if not QDRANT_URL:
    raise ValueError("QDRANT_URL is missing from .env")

if not QDRANT_API_KEY:
    raise ValueError("QDRANT_API_KEY is missing from .env")


# ============================================================
# 2. Connect to Qdrant Cloud
# ============================================================

client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)

print("Connected to Qdrant")


# ============================================================
# 3. Load Dense Embedding Model
# ============================================================

dense_model = SentenceTransformer(
    "BAAI/bge-m3"
)

print("Dense model loaded")


# ============================================================
# 4. Load Sparse BM25 Model
# ============================================================

sparse_model = SparseTextEmbedding(
    model_name="Qdrant/bm25"
)

print("Sparse BM25 model loaded")


# ============================================================
# 5. Load Reranker
# ============================================================

reranker = CrossEncoder(
    "BAAI/bge-reranker-base"
)

print("Reranker loaded")


# ============================================================
# 6. Retrieval Function
# ============================================================

def retrieve(question, retrieval_limit=20, final_limit=5):

    print("\nQuestion:")
    print(question)

    # --------------------------------------------------------
    # Dense query
    # --------------------------------------------------------

    query_dense = dense_model.encode(
        question,
        normalize_embeddings=True
    )

    # --------------------------------------------------------
    # Sparse query
    # --------------------------------------------------------

    query_sparse = list(
        sparse_model.query_embed(question)
    )[0]

    # --------------------------------------------------------
    # Hybrid Search + RRF
    # --------------------------------------------------------

    results = client.query_points(

        collection_name=COLLECTION_NAME,

        prefetch=[

            models.Prefetch(
                query=query_dense.tolist(),
                using="dense",
                limit=retrieval_limit
            ),

            models.Prefetch(
                query=models.SparseVector(
                    indices=query_sparse.indices.tolist(),
                    values=query_sparse.values.tolist()
                ),
                using="sparse",
                limit=retrieval_limit
            )
        ],

        query=models.FusionQuery(
            fusion=models.Fusion.RRF
        ),

        limit=10,

        with_payload=True
    )

    print(
        f"\nRetrieved {len(results.points)} candidates"
    )

    # --------------------------------------------------------
    # Convert Qdrant results
    # --------------------------------------------------------

    candidate_docs = []

    for point in results.points:

        candidate_docs.append({

            "text": point.payload.get("text"),

            "source": point.payload.get("source"),

            "page": point.payload.get("page"),

            "rrf_score": point.score
        })

    # --------------------------------------------------------
    # Reranking
    # --------------------------------------------------------

    pairs = [
        [question, doc["text"]]
        for doc in candidate_docs
    ]

    rerank_scores = reranker.predict(pairs)

    for doc, score in zip(
        candidate_docs,
        rerank_scores
    ):

        doc["rerank_score"] = float(score)

    # --------------------------------------------------------
    # Sort by reranker score
    # --------------------------------------------------------

    reranked_docs = sorted(
        candidate_docs,
        key=lambda x: x["rerank_score"],
        reverse=True
    )

    top_docs = reranked_docs[:final_limit]

    # --------------------------------------------------------
    # Print Top Documents
    # --------------------------------------------------------

    print("\n" + "=" * 80)
    print("TOP RERANKED DOCUMENTS")
    print("=" * 80)

    for i, doc in enumerate(top_docs, 1):

        print("\n" + "-" * 80)

        print(f"RESULT: {i}")
        print(f"SOURCE: {doc['source']}")
        print(f"PAGE: {doc['page']}")
        print(f"RRF SCORE: {doc['rrf_score']}")
        print(f"RERANK SCORE: {doc['rerank_score']}")

        print("\nTEXT:")
        print(doc["text"][:1200])

    # --------------------------------------------------------
    # Build Context
    # --------------------------------------------------------

    context_parts = []

    for i, doc in enumerate(top_docs, 1):

        context = f"""
SOURCE {i}
Paper: {doc['source']}
Page: {doc['page']}

{doc['text']}
"""

        context_parts.append(context)

    context_text = "\n\n".join(context_parts)

    return top_docs, context_text