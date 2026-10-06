import re
import time
from typing import Optional, Tuple, Dict, Any
import chromadb
from fastembed import TextEmbedding

CRITICAL_NEGATION_TOKENS = {"not", "no", "without", "never", "except", "only", "neither", "nor"}
TEMPORAL_REGEX = re.compile(r"\b(today|now|current|latest|live|weather|stock|price|score|yesterday|tomorrow)\b", re.I)

class SemanticCache:
    def __init__(self, persist_dir: str = "./chroma_cache"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name="sentry_semantic_cache",
            metadata={"hnsw:space": "cosine"}
        )
        self.embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

    def _extract_tokens(self, text: str) -> set:
        return set(re.findall(r"\b\w+\b", text.lower()))

    def query(self, prompt: str, tenant_id: str = "default", threshold: float = 0.92) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]], float]:
        start_time = time.time()
        
        # 1. Temporal bypass
        if TEMPORAL_REGEX.search(prompt):
            return False, None, None, round((time.time() - start_time) * 1000, 2)

        prompt_tokens = self._extract_tokens(prompt)
        prompt_embedding = list(self.embedder.embed([prompt]))[0].tolist()

        # 2. Query vector store filtered by tenant
        results = self.collection.query(
            query_embeddings=[prompt_embedding],
            n_results=1,
            where={"tenant_id": tenant_id}
        )

        if not results or not results["documents"] or len(results["documents"][0]) == 0:
            return False, None, None, round((time.time() - start_time) * 1000, 2)

        distance = results["distances"][0][0]
        similarity = 1.0 - distance
        cached_prompt = results["metadatas"][0][0].get("prompt", "")
        cached_response = results["documents"][0][0]
        cached_meta = results["metadatas"][0][0]

        # 3. Check similarity threshold
        if similarity < threshold:
            return False, None, None, round((time.time() - start_time) * 1000, 2)

        # 4. Polarity guard (prevent false hits on negations)
        cached_tokens = self._extract_tokens(cached_prompt)
        prompt_neg = prompt_tokens.intersection(CRITICAL_NEGATION_TOKENS)
        cached_neg = cached_tokens.intersection(CRITICAL_NEGATION_TOKENS)

        if prompt_neg != cached_neg:
            return False, None, None, round((time.time() - start_time) * 1000, 2)

        latency = round((time.time() - start_time) * 1000, 2)
        return True, cached_response, cached_meta, latency

    def set(self, prompt: str, response: str, tenant_id: str = "default", model_used: str = "unknown"):
        prompt_embedding = list(self.embedder.embed([prompt]))[0].tolist()
        doc_id = f"{tenant_id}_{abs(hash(prompt))}_{int(time.time() * 1000)}"
        
        self.collection.add(
            ids=[doc_id],
            embeddings=[prompt_embedding],
            documents=[response],
            metadatas=[{
                "prompt": prompt,
                "tenant_id": tenant_id,
                "model_used": model_used,
                "timestamp": time.time()
            }]
        )
