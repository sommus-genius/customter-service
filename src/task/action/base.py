from abc import ABC
from abc import abstractmethod
from typing import Any

from pydantic import BaseModel

from domain.messages import BotMessage
from domain.state import DialogueState

class ActionResult(BaseModel):
    """
    所有Action的统一返回结果
    """
    messages: list[BotMessage] = [] #返回给用户的消息
    slot_updates: dict[str,Any] = {} #要收集的槽位信息


class Action(ABC):
    name: str #Action的名字

    @abstractmethod
    async def run(
            self,
            state:DialogueState,
            action_kwargs:dict[str, Any]
    ) -> ActionResult:
        """
        执行Action
        :param state:
        :param action_kwargs: action的args参数
        :return:
        """
        pass



