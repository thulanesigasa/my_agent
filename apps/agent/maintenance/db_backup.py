"""
Database Vector Memory Backup Script.
Exports langgraph_memory pgvector table in memory-safe chunks and uploads daily backup archives to cloud storage.
"""
import os
import json
import gzip
import logging
import datetime
from typing import List, Dict, Any
from supabase import create_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("agent.maintenance.backup")


def run_database_vector_backup():
    """
    Exports langgraph_memory table rows in chunks of 500 records and writes a compressed JSON archive.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        logger.error("Supabase credentials missing. Cannot execute database vector backup.")
        return False

    client = create_client(supabase_url, supabase_key)
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_langgraph_memory_{timestamp}.json.gz"
    
    logger.info(f"Starting chunked export of 'langgraph_memory' pgvector table...")

    page_size = 500
    offset = 0
    all_records: List[Dict[str, Any]] = []

    try:
        while True:
            logger.info(f"Exporting records {offset} to {offset + page_size}...")
            res = client.table("langgraph_memory").select("id, namespace, key, value, created_at").range(offset, offset + page_size - 1).execute()
            records = res.data or []
            if not records:
                break

            all_records.extend(records)
            offset += page_size
            if len(records) < page_size:
                break

        logger.info(f"Successfully retrieved {len(all_records)} memory records. Compressing backup archive...")

        # Compress to JSON gzip
        json_bytes = json.dumps(all_records, default=str).encode("utf-8")
        compressed_bytes = gzip.compress(json_bytes)

        # Upload to Supabase Storage bucket 'backups' if bucket exists
        try:
            client.storage.from_("backups").upload(
                path=backup_filename,
                file=compressed_bytes,
                file_options={"content-type": "application/gzip"}
            )
            logger.info(f"Backup archive '{backup_filename}' successfully uploaded to Supabase Storage 'backups' bucket.")
        except Exception as storage_err:
            logger.warning(f"Cloud bucket upload notice: {storage_err}. Writing backup archive locally...")
            os.makedirs("backups", exist_ok=True)
            with open(os.path.join("backups", backup_filename), "wb") as f:
                f.write(compressed_bytes)
            logger.info(f"Local backup archive saved to 'backups/{backup_filename}'.")

        return True

    except Exception as e:
        logger.error(f"Error executing vector database backup: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    run_database_vector_backup()
