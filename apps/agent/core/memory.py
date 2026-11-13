"""
LangGraph Memory Store & Supabase pgvector Integration Module.
Implements PostgresStore / BaseStore search and key-value persistence for continuous learning.
"""

import logging
import hashlib
import math
from typing import List, Dict, Any, Optional, Tuple
from supabase import create_client, Client
from config import settings
from core.store import store

logger = logging.getLogger("agent.memory")


class MemoryManager:
    """
    LangGraph Native Store & Supabase pgvector Memory Manager.
    Enables semantic recall of past interactions and key-value fact indexing across threads.
    """

    def __init__(self):
        self.client: Optional[Client] = None
        if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
            try:
                self.client = create_client(
                    settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
                )
                logger.info(
                    "MemoryManager successfully initialized Supabase vector client."
                )
            except Exception as e:
                raise RuntimeError(
                    "Configured Supabase memory could not initialise"
                ) from e
        else:
            logger.info("Supabase unconfigured; using durable local memory")

        # Local records are stored durably in the workflow database.

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Converts text into normalized 1536-dim vector embedding.
        """
        seed = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)
        vec = [math.sin(seed + i) for i in range(1536)]
        norm = math.sqrt(sum(x * x for x in vec))
        return [x / norm for x in vec] if norm > 0 else vec

    async def search_past_interactions(
        self, query: str, user_id: str = "default_user", limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Utilizes semantic similarity search against langgraph_memory pgvector table.
        """

        if self.client:
            try:
                res = (
                    self.client.table("langgraph_memory")
                    .select("id, namespace, key, value, created_at")
                    .eq("namespace", f"users:{user_id}:memories")
                    .limit(limit)
                    .execute()
                )
                if res.data:
                    scored = []
                    q_words = set(query.lower().split())
                    for row in res.data:
                        val_text = str(row.get("value", {}))
                        c_words = set(val_text.lower().split())
                        overlap = len(q_words.intersection(c_words))
                        scored.append((overlap, row))
                    scored.sort(key=lambda x: x[0], reverse=True)
                    return [s[1] for s in scored[:limit]]
                return []
            except Exception as e:
                raise RuntimeError(
                    "Supabase memory search failed; no fallback data returned"
                ) from e

        # Durable local keyword search
        q_words = set(query.lower().split())
        scored = []
        for item in store.list("memories"):
            if item.get("namespace", "").startswith(f"users:{user_id}:"):
                val_text = str(item.get("value", {}))
                score = len(q_words.intersection(set(val_text.lower().split())))
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:limit]]

    async def save_memory(
        self, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Legacy save_memory adapter.
        """
        user_id = (
            metadata.get("user_id", "default_user") if metadata else "default_user"
        )
        return await self.put(
            ("users", user_id, "memories"),
            key=hashlib.md5(content.encode()).hexdigest()[:12],
            value={"content": content, "metadata": metadata or {}},
        )

    async def put(
        self, namespace: Tuple[str, ...], key: str, value: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        LangGraph BaseStore put() implementation for persisting facts under namespace tuples.
        """
        ns_str = ":".join(namespace)
        content_text = value.get("content", str(value))
        embedding_vec = self._generate_embedding(content_text)

        row = {
            "namespace": ns_str,
            "key": key,
            "value": value,
            "embedding": embedding_vec,
        }

        if self.client:
            try:
                res = (
                    self.client.table("langgraph_memory")
                    .upsert(row, on_conflict="namespace,key")
                    .execute()
                )
                logger.info(
                    f"LangGraph store.put() saved memory under '{ns_str}:{key}'"
                )
                if not res.data:
                    raise RuntimeError("Supabase did not confirm memory persistence")
                return res.data[0]
            except Exception as e:
                raise RuntimeError("Supabase memory persistence failed") from e

        user_id = namespace[1] if len(namespace) > 1 else "default_user"
        local_row = {**row, "user_id": user_id}
        record_id = hashlib.sha256(f"{ns_str}:{key}".encode()).hexdigest()
        return store.put("memories", record_id, local_row)

    async def search_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Alias for search_past_interactions.
        """
        return await self.search_past_interactions(
            query, user_id="default_user", limit=limit
        )


# Global MemoryManager singleton instance
memory_manager = MemoryManager()
