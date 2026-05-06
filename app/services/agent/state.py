from typing import Dict, Any, Sequence
from typing_extensions import TypedDict, Annotated

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    retrieved_context: str
    user_info: Dict[str, Any]
    next_step: str