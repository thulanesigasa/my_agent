"""
CRM Service: Structured database layer for T.S Industries clients and project sales pipeline in Supabase.
"""
import logging
from typing import Dict, Any, Optional, List
from config import settings

logger = logging.getLogger("agent.crm_service")

# Memory / In-memory fallback CRM store if Supabase client is unconfigured
IN_MEMORY_CLIENTS: Dict[str, Dict[str, Any]] = {}
IN_MEMORY_PROJECTS: Dict[str, Dict[str, Any]] = {}


def _get_supabase_client():
    """
    Returns configured Supabase client or None.
    """
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        try:
            from supabase import create_client
            return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        except Exception as e:
            logger.warning(f"Supabase client initialization warning: {e}")
    return None


async def upsert_client(
    name: str,
    email: str,
    phone: str = "",
    company: str = ""
) -> Dict[str, Any]:
    """
    Creates or updates a client record in Supabase (or fallback in-memory CRM).
    """
    email_clean = email.lower().strip()
    if not name:
        name = email_clean.split("@")[0].capitalize()

    client = _get_supabase_client()
    if client:
        try:
            res = client.table("clients").select("*").eq("email", email_clean).execute()
            if res.data:
                existing_id = res.data[0]["id"]
                update_data = {"name": name}
                if phone:
                    update_data["phone"] = phone
                if company:
                    update_data["company"] = company

                up_res = client.table("clients").update(update_data).eq("id", existing_id).execute()
                logger.info(f"Updated client CRM record for '{email_clean}'")
                return up_res.data[0] if up_res.data else res.data[0]
            else:
                new_data = {"name": name, "email": email_clean, "phone": phone, "company": company}
                ins_res = client.table("clients").insert(new_data).execute()
                logger.info(f"Created new client CRM record for '{email_clean}'")
                return ins_res.data[0] if ins_res.data else new_data
        except Exception as e:
            logger.error(f"Supabase client upsert error: {e}")

    # Fallback in-memory CRM store
    if email_clean in IN_MEMORY_CLIENTS:
        client_record = IN_MEMORY_CLIENTS[email_clean]
        client_record["name"] = name
        if phone:
            client_record["phone"] = phone
        if company:
            client_record["company"] = company
    else:
        client_record = {
            "id": f"cli_{len(IN_MEMORY_CLIENTS) + 1:03d}",
            "name": name,
            "email": email_clean,
            "phone": phone,
            "company": company,
            "created_at": "Just now"
        }
        IN_MEMORY_CLIENTS[email_clean] = client_record

    logger.info(f"Upserted client CRM record for '{email_clean}' (Fallback mode)")
    return client_record


async def update_project_status(
    client_email: str,
    status: str,
    quoted_price: float = 0.0,
    scope_summary: str = ""
) -> Dict[str, Any]:
    """
    Moves a client through the sales pipeline ('Lead', 'Quoted', 'In Progress', 'Completed', 'Lost').
    Creates or updates the project record linked to the client.
    """
    email_clean = client_email.lower().strip()
    client_record = await upsert_client(name="", email=email_clean)

    client = _get_supabase_client()
    if client and client_record.get("id"):
        try:
            client_id = client_record["id"]
            res = client.table("projects").select("*").eq("client_id", client_id).execute()

            project_payload: Dict[str, Any] = {
                "client_id": client_id,
                "status": status,
            }
            if quoted_price > 0:
                project_payload["quoted_price"] = quoted_price
            if scope_summary:
                project_payload["scope_summary"] = scope_summary

            if res.data:
                proj_id = res.data[0]["id"]
                up_res = client.table("projects").update(project_payload).eq("id", proj_id).execute()
                logger.info(f"Updated project status to '{status}' for '{email_clean}'")
                return up_res.data[0] if up_res.data else res.data[0]
            else:
                ins_res = client.table("projects").insert(project_payload).execute()
                logger.info(f"Created new project with status '{status}' for '{email_clean}'")
                return ins_res.data[0] if ins_res.data else project_payload
        except Exception as e:
            logger.error(f"Supabase project status update error: {e}")

    # Fallback in-memory CRM
    proj_record = IN_MEMORY_PROJECTS.get(email_clean, {})
    proj_record.update({
        "client_email": email_clean,
        "status": status,
        "quoted_price": quoted_price or proj_record.get("quoted_price", 0.0),
        "scope_summary": scope_summary or proj_record.get("scope_summary", ""),
        "updated_at": "Just now"
    })
    IN_MEMORY_PROJECTS[email_clean] = proj_record
    logger.info(f"Updated project status to '{status}' for '{email_clean}' (Fallback mode)")
    return proj_record


async def get_client_and_projects(email: str) -> Dict[str, Any]:
    """
    Fetches full CRM details for a given client email.
    """
    email_clean = email.lower().strip()
    client = _get_supabase_client()
    if client:
        try:
            res_c = client.table("clients").select("*").eq("email", email_clean).execute()
            if res_c.data:
                client_data = res_c.data[0]
                res_p = client.table("projects").select("*").eq("client_id", client_data["id"]).execute()
                return {"client": client_data, "projects": res_p.data or []}
        except Exception as e:
            logger.error(f"Error fetching CRM details: {e}")

    return {
        "client": IN_MEMORY_CLIENTS.get(email_clean, {}),
        "projects": [IN_MEMORY_PROJECTS.get(email_clean, {})] if email_clean in IN_MEMORY_PROJECTS else []
    }
