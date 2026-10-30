from typing import Any

from domain.state import DialogueState
from task.action.base import Action, ActionResult


class ActionListen(Action):
    """
    等待用户输入槽位信息，不进行任何处理，用于等待用户输入槽位信息
    """
    name = "action_listen"

    async def run(
            self,
            state:DialogueState,
            action_kwargs:dict[str, Any]
    ) -> ActionResult:
        return ActionResult()