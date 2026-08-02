from typing import Any

from backend.services.classifier_stream import classifier_stream
from backend.services.proxy_agent import ProxyState
from backend.services.proxy_manager import proxy_manager
from shared.services.state_hub import StateHub

# The agent drives itself through these while reconnecting, so they are more
# accurate than whatever the manager last recorded.
AGENT_OWNED_STATUS = {"reconnecting", "connecting", "disconnected", "login_failed"}

# ...unless the manager is in a state the agent cannot know about.
MANAGER_OWNED_STATUS = {"Login Failed", "Connect Failed", "Config Missing"}

WATCH_INTERVAL = 1.0


def management_snapshot() -> dict[str, Any]:
    status = proxy_manager.status
    agent = proxy_manager.agent
    if (
        agent
        and agent.status in AGENT_OWNED_STATUS
        and status not in MANAGER_OWNED_STATUS
    ):
        status = agent.status.replace("_", " ").title()

    return {
        "status": status,
        "classifier_status": "Connected" if classifier_stream.connected else "Disconnected",
        "server_id": agent.server_id if agent else None,
        "config": ProxyState.serialize(),
    }


# Proxy and classifier sockets drop without anyone calling an endpoint, so the
# hub re-reads this snapshot itself and pushes only when it changes.
management_hub = StateHub(management_snapshot, poll_interval=WATCH_INTERVAL)
