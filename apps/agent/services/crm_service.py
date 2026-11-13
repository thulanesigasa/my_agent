"""CRM uses configured Supabase or an explicit durable local store, never a silent fallback."""

from config import settings
from core.store import store


def _get_supabase_client():
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        from supabase import create_client

        return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    return None


async def upsert_client(name, email, phone="", company=""):
    email = email.lower().strip()
    if not email:
        raise ValueError("Client email is required")
    client = _get_supabase_client()
    if client:
        records = client.table("clients").select("*").eq("email", email).execute().data
    else:
        records = [r for r in store.list("clients") if r["email"] == email]
    previous = records[0] if records else {}
    data = {
        "email": email,
        "name": name or previous.get("name") or email.split("@")[0],
        "phone": phone or previous.get("phone", ""),
        "company": company or previous.get("company", ""),
    }
    if client:
        result = client.table("clients").upsert(data, on_conflict="email").execute()
        if not result.data:
            raise RuntimeError("CRM did not confirm client persistence")
        return result.data[0]
    return store.put("clients", previous.get("id", email), data)


async def update_project_status(
    client_email, status, quoted_price=0.0, scope_summary=""
):
    if status not in ("Lead", "Quoted", "In Progress", "Completed", "Lost"):
        raise ValueError("Unsupported CRM status")
    customer = await upsert_client("", client_email)
    client = _get_supabase_client()
    if client:
        previous = (
            client.table("projects")
            .select("*")
            .eq("client_id", customer["id"])
            .execute()
            .data
        )
    else:
        previous = [
            p for p in store.list("projects") if p["client_id"] == customer["id"]
        ]
    data = {"client_id": customer["id"], "status": status}
    if quoted_price:
        data["quoted_price"] = quoted_price
    if scope_summary:
        data["scope_summary"] = scope_summary
    if client:
        query = client.table("projects")
        result = (
            query.update(data).eq("id", previous[0]["id"])
            if previous
            else query.insert(data)
        ).execute()
        if not result.data:
            raise RuntimeError("CRM did not confirm project persistence")
        return result.data[0]
    old = previous[0] if previous else {}
    return store.put("projects", old.get("id", customer["id"]), {**old, **data})


async def get_all_clients():
    client = _get_supabase_client()
    return (
        client.table("clients").select("*").execute().data
        if client
        else store.list("clients")
    )


async def get_all_projects():
    client = _get_supabase_client()
    return (
        client.table("projects").select("*").execute().data
        if client
        else store.list("projects")
    )


async def get_client_and_projects(email):
    customer = next(
        (c for c in await get_all_clients() if c["email"] == email.lower().strip()), {}
    )
    projects = [
        p for p in await get_all_projects() if p["client_id"] == customer.get("id")
    ]
    return {"client": customer, "projects": projects}
