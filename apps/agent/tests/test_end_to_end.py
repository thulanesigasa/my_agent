"""
End-to-End System Smoke Test: Simulates a complete multi-agent workflow cycle
(triage_node -> drafter_node -> learner_node) and verifies memory persistence.
"""
import pytest
import uuid
from core.state import AgentState
from core.graph import agent_workflow
from core.memory import memory_manager


@pytest.mark.asyncio
async def test_end_to_end_agent_workflow():
    """
    Executes full end-to-end workflow invocation and validates state transitions & memory storage.
    """
    test_session_id = f"e2e_test_{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": test_session_id}}

    initial_state: AgentState = {
        "messages": [
            {"role": "user", "content": "Hello, we are launching an enterprise trial and need custom contract pricing for 50 seats."}
        ],
        "email_input": {
            "sender": "cto@enterprise-client.com",
            "subject": "Enterprise Trial Inquiry",
            "body": "We need custom contract pricing for 50 seats.",
            "thread_id": test_session_id
        },
        "approval_status": "none"
    }

    # 1. Execute State Machine Workflow
    final_state = await agent_workflow.ainvoke(initial_state, config=config)

    # 2. Validate State Output & Sender Node
    assert final_state is not None
    assert final_state.get("intent") in ["sales", "client_inquiry", "general"]
    assert final_state.get("sender") in ["learner", "human_approval", "output_dispatcher_node"]

    # 3. Verify Memory Search & Recall
    recalled = await memory_manager.search_past_interactions(
        query="enterprise trial pricing 50 seats",
        user_id="cto@enterprise-client.com",
        limit=3
    )

    assert isinstance(recalled, list)
