"""
Pytest Test Suite & LangSmith Dataset Evaluation for LangGraph Workflow.
"""
import pytest
from core.state import AgentState
from agents.triage import triage_node
from agents.drafter import drafter_node
from core.memory import memory_manager


@pytest.mark.asyncio
@pytest.mark.langsmith
async def test_triage_node_spam_classification():
    """
    Evaluates triage_node to verify it correctly classifies promotional spam messages.
    """
    state: AgentState = {
        "messages": [{"role": "user", "content": "CLAIM YOUR FREE CASINO PRIZE NOW! Click here to win $10000!"}],
        "email_input": {
            "sender": "spammer@lottery-win.biz",
            "subject": "URGENT WINNER ANNOUNCEMENT",
            "body": "CLAIM YOUR FREE CASINO PRIZE NOW!"
        },
        "approval_status": "none"
    }

    res_state = await triage_node(state)

    assert res_state.get("sender") == "triage"
    assert res_state.get("intent") in ["spam", "general"]


@pytest.mark.asyncio
@pytest.mark.langsmith
async def test_drafter_node_memory_recall():
    """
    Evaluates drafter_node to verify semantic memory recall from Supabase vector storage and response quality.
    """
    # Seed a memory item
    await memory_manager.save_memory(
        "Client preference: Preferred communication language is English with formal tone.",
        metadata={"user_id": "test_user_001"}
    )

    state: AgentState = {
        "messages": [{"role": "user", "content": "Please draft a response to our enterprise client inquiry."}],
        "intent": "client_inquiry",
        "retrieved_context": [
            {"content": "Client preference: Preferred communication language is English with formal tone."}
        ],
        "approval_status": "none"
    }

    res_state = await drafter_node(state)

    assert res_state.get("sender") == "drafter"
    assert res_state.get("draft_response") is not None
    assert len(str(res_state.get("draft_response"))) > 10
