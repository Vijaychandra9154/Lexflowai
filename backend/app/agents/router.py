"""
LexFlowAI Agent Router
----------------------
This module decides which AI agents should run
based on the user's intent.

Version: v0.2.0
"""

from typing import List


def route_intent(intent: str) -> List[str]:
    """
    Returns a list of agents that should process
    the user's request.
    """

    intent = intent.lower()

    agents = []

    # Drafting
    if any(word in intent for word in [
        "draft",
        "reply",
        "petition",
        "notice",
        "application",
        "complaint"
    ]):
        agents.append("draft_agent")

    # Forum Intelligence
    if any(word in intent for word in [
        "lokayukta",
        "women",
        "human rights",
        "district court",
        "high court",
        "supreme court",
        "consumer",
        "rti"
    ]):
        agents.append("forum_agent")

    # Memory Agent
    agents.append("memory_agent")

    # Lawyer Preference Agent
    agents.append("preference_agent")

    # Remove duplicates while preserving order
    agents = list(dict.fromkeys(agents))

    return agents


if __name__ == "__main__":

    sample = (
        "Draft a reply before Lokayukta "
        "regarding road construction delay."
    )

    print(route_intent(sample))