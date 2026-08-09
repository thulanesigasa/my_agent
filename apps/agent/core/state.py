from typing import TypedDict, List, Dict, Any, Optional
from typing_extensions import Annotated
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    """
    Shared AgentState passed across LangGraph nodes in the state machine.
    """
    # Chat message history with automated message reducer
    messages: Annotated[List[Dict[str, Any]], add_messages]
    
    # Active user intent (e.g., 'triage', 'draft_response', 'email_dispatch', 'whatsapp_dispatch', 'general_qa')
    intent: str
    
    # Retrieved memories from Supabase pgvector semantic search
    retrieved_memory: List[Dict[str, Any]]
    
    # Context payload for email operations
    email_context: Dict[str, Any]
    
    # Drafted response synthesized by Drafter (Gemini 1.5 Pro)
    draft_response: str
    
    # Base64 encoded or binary audio payload for TTS / STT
    audio_payload: Optional[str]
    
    # Flag indicating whether human approval is required for high-risk action
    requires_human_approval: bool
    
    # Status of approval: 'pending', 'approved', 'rejected'
    approval_status: str
    
    # Proposed external tool action payload (e.g. email details, WhatsApp text)
    proposed_action: Optional[Dict[str, Any]]
    
    # Extracted facts/learnings to be indexed into memory
    extracted_learnings: List[str]
    
    # Current active agent node executing
    active_node: str
    
    # Error message if any step failed
    error: Optional[str]
