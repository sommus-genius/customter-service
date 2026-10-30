from typing import Any

from pydantic import BaseModel
from sqlalchemy.util import await_

from domain.state import DialogueState
from task.action.base import ActionResult
from task.action.registory import ActionRegistry


class ActionCall(BaseModel):
    action_name:str
    action_kwargs:dict[str,Any] = {}



class ActionRunner:
    def __init__(self,registry:ActionRegistry) -> None:
        self.registry = registry


    async def run(self,action_call:ActionCall,state: DialogueState) -> ActionResult:

        # 1.获取Action的名字
        action_name = action_call.action_name

        # 2.根据名字从注册中心获取Action对象的实例
        action = self.registry.get(action_name)

        # 3.调用Action的业务逻辑
        return await action.run(state,action_call.action_kwargs)