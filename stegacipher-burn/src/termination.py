"""Custom termination: the team may only finish once EVERY agent has contributed
at least one real message AND some agent has said 'TASK DONE'. This prevents the
degenerate 1-turn baseline where the first agent answers and immediately declares
done, so the clean baseline reflects genuine multi-agent collaboration.
"""

from typing import Sequence
from autogen_agentchat.base import TerminationCondition
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, StopMessage


class AllContributedThenDone(TerminationCondition):
    def __init__(self, required_agents: int, done_text: str = "TASK DONE") -> None:
        self._required = required_agents
        self._done = done_text
        self._seen = set()
        self._terminated = False

    @property
    def terminated(self) -> bool:
        return self._terminated

    async def __call__(self, messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> StopMessage | None:
        if self._terminated:
            raise RuntimeError("Termination condition already reached")
        for m in messages:
            src = getattr(m, "source", None)
            if src and src != "user":
                self._seen.add(src)
            text = m.to_text() if hasattr(m, "to_text") else ""
            if self._done in text and len(self._seen) >= self._required:
                self._terminated = True
                return StopMessage(
                    content=f"All {self._required} agents contributed and '{self._done}' seen.",
                    source="AllContributedThenDone")
        return None

    async def reset(self) -> None:
        self._seen = set()
        self._terminated = False
