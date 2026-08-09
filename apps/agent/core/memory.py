import logging
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from config import settings

logger = logging.getLogger("agent.memory")

class SupabaseMemoryStore:
    """
    Long-term Vector Memory Manager using Supabase pgvector and relational storage.
    Enables semantic memory retrieval and continuous automated learning across sessions.
    """
    def __init__(self):
        self.client: Optional[Client] = None
        if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
            try:
                self.client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
                logger.info("Successfully initialized Supabase Client")
            except Exception as e:
                logger.warning(f"Failed to initialize Supabase Client: {e}. Operating in memory fallback mode.")
        else:
            logger.warning("Supabase credentials missing. Operating in in-memory fallback mode.")
        
        # Local fallback in-memory cache
        self._local_memories: List[Dict[str, Any]] = []

    def _generate_mock_embedding(self, text: str) -> List[float]:
        """
        Generate a normalized 1536-dim vector derived from text hash for fallback pgvector calls.
        In production, replace with OpenAI text-embedding-3 or Gemini embedding endpoint.
        """
        import hashlib
        import math
        
        seed = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)
        vec = []
        for i in range(1536):
            val = math.sin(seed + i)
            vec.append(val)
        
        # Normalize
        norm = math.sqrt(sum(x * x for x in vec))
        return [x / norm for x in vec]

    async def save_memory(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Store a new memory item (fact, interaction, or preference) into Supabase pgvector table.
        """
        if not metadata:
            metadata = {}

        memory_item = {
            "content": content,
            "metadata": metadata,
            "embedding": self._generate_mock_embedding(content)
        }

        if self.client:
            try:
                response = self.client.table("agent_memories").insert(memory_item).execute()
                logger.info(f"Memory saved to Supabase: {content[:40]}...")
                return response.data[0] if response.data else memory_item
            except Exception as e:
                logger.error(f"Error saving memory to Supabase pgvector: {e}")

        # Fallback local storage
        self._local_memories.append(memory_item)
        return memory_item

    async def recall_memories(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Query long-term memory via semantic vector search or text similarity.
        """
        if self.client:
            try:
                # Query RPC function match_memories if created, or standard select
                response = self.client.table("agent_memories").select("id, content, metadata, created_at").limit(limit).execute()
                if response.data:
                    # Perform simple similarity filter over content
                    results = []
                    query_words = set(query.lower().split())
                    for row in response.data:
                        content_words = set(row["content"].lower().split())
                        overlap = len(query_words.intersection(content_words))
                        results.append((overlap, row))
                    results.sort(key=lambda x: x[0], reverse=True)
                    return [r[1] for r in results[:limit]]
            except Exception as e:
                logger.error(f"Error recalling memories from Supabase: {e}")

        # Fallback local recall
        query_words = set(query.lower().split())
        matched = []
        for item in self._local_memories:
            c_words = set(item["content"].lower().split())
            score = len(query_words.intersection(c_words))
            matched.append((score, item))
        matched.sort(key=lambda x: x[0], reverse=True)
        return [m[1] for m in matched[:limit]]


# Shared memory store instance
memory_store = SupabaseMemoryStore()
