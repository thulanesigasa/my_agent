"""
AgentState TypedDict definition for LangGraph multi-agent orchestration.
"""
from typing import TypedDict, List, Dict, Any, Optional, Union
from typing_extensions import Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict, total=False):
    """
    Shared state container passed between LangGraph nodes.
    """
    # Conversation message history (HumanMessage, AIMessage, SystemMessage)
    messages: Annotated[List[Union[BaseMessage, Dict[str, Any]]], add_messages]

    # Node identifier of the current active worker or user (e.g. 'triage', 'drafter', 'learner')
    sender: str

    # Optional email context payload ({'sender': ..., 'subject': ..., 'body': ..., 'thread_id': ...})
    email_input: Optional[Dict[str, Any]]

    # Classified user intent ('sales', 'support', 'client_inquiry', 'general', 'spam')
    intent: str

    # Context memories retrieved from Supabase pgvector vector store
    retrieved_context: List[Dict[str, Any]]

    # Generated message or email response draft
    draft_response: Optional[str]

    # Flag for human-in-the-loop approval gate on high-risk actions
    needs_human_approval: bool

    # Approval status ('pending', 'approved', 'rejected')
    approval_status: Optional[str]

    # Final output response payload (text or voice audio base64)
    final_output: Optional[Union[str, Dict[str, Any]]]

    # Extracted learnings/facts to index in Supabase pgvector
    extracted_learnings: List[str]
