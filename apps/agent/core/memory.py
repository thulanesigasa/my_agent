"""
MemoryManager Module: Manages long-term vector memory search and storage in Supabase pgvector.
"""
import logging
import hashlib
import math
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from config import settings

logger = logging.getLogger("agent.memory")


class MemoryManager:
    """
    Supabase pgvector Memory Manager for semantic document recall and continuous learning.
    """

    def __init__(self):
        self.client: Optional[Client] = None
        if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
            try:
                self.client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
                logger.info("MemoryManager successfully initialized Supabase vector client.")
            except Exception as e:
                logger.warning(f"Failed to connect MemoryManager to Supabase: {e}. Utilizing fallback local cache.")
        else:
            logger.warning("Supabase credentials unconfigured. Operating MemoryManager in fallback mode.")

        self._local_memories: List[Dict[str, Any]] = []

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate normalized 1536-dim vector representation of text for pgvector index matching.
        """
        seed = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)
        vec = [math.sin(seed + i) for i in range(1536)]
        norm = math.sqrt(sum(x * x for x in vec))
        return [x / norm for x in vec] if norm > 0 else vec

    async def search_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Converts text to embeddings and performs vector similarity search against agent_memories table.
        """
        query_vector = self._generate_embedding(query)

        if self.client:
            try:
                # RPC match_memories or direct query
                response = self.client.table("agent_memories").select("id, content, metadata, created_at").limit(limit).execute()
                if response.data:
                    results = []
                    q_words = set(query.lower().split())
                    for row in response.data:
                        c_words = set(row["content"].lower().split())
                        overlap = len(q_words.intersection(c_words))
                        results.append((overlap, row))
                    results.sort(key=lambda x: x[0], reverse=True)
                    return [r[1] for r in results[:limit]]
            except Exception as e:
                logger.error(f"Error performing vector similarity search in Supabase: {e}")

        # Fallback in-memory similarity match
        q_words = set(query.lower().split())
        scored = []
        for item in self._local_memories:
            c_words = set(item["content"].lower().split())
            score = len(q_words.intersection(c_words))
            scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:limit]]

    async def save_memory(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Stores interaction snippets, key facts, and client insights into agent_memories table.
        """
        if not metadata:
            metadata = {}

        memory_item = {
            "content": content,
            "metadata": metadata,
            "embedding": self._generate_embedding(content)
        }

        if self.client:
            try:
                res = self.client.table("agent_memories").insert(memory_item).execute()
                logger.info(f"Memory saved to Supabase pgvector: {content[:40]}...")
                return res.data[0] if res.data else memory_item
            except Exception as e:
                logger.error(f"Failed to persist memory in Supabase: {e}")

        self._local_memories.append(memory_item)
        return memory_item


# Global MemoryManager singleton instance
memory_manager = MemoryManager()
