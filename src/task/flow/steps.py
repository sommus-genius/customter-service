from enum import Enum
from typing import List
from pydantic import BaseModel
from task.flow.links import ConditionalLink, FallbackLink,FlowStepLink, StaticLink


class ResponseDefinition(BaseModel):
    """
    响应模式：
    static：静态模式
    rephrase：改写模式（LLM）
    """
    text: str #AI的恢复，必填
    model: str = "static" #响应的方式，可选，默认静态
    prompt: str | None = None

class FlowStepType(Enum):
    """
    流程的步骤类型
    """
    START = "start"
    END = "end"
    ACTION = "action"
    COLLECT = "collect"

class FlowStep(BaseModel):
    """
    流程的步骤
    """
    id: str #步骤id，必填
    type: FlowStepType #步骤类型，必填
    next: List[FlowStepLink] =[] #下一步的步骤id
    description: str = "" #步骤描述

    @classmethod
    def from_dict(cls, data: dict) -> "FlowStep":
        step_type = data["type"]
        clz = STEP_TYPE_TO_CLASS[step_type]
        return clz.from_dict(data)

    @staticmethod
    def base_fields(data: dict) -> dict:
        return {
            "id": data["id"],
            "type": data["type"],
            "next": FlowStep.build_links(data["next"]),
            "description": data.get("description", ""),
        }
    @staticmethod
    def build_links(link_data: list | str) -> List[FlowStepLink]:
        #1.next是字符串
        if isinstance(link_data, str):
            return [StaticLink(target=link_data)]
        #2.next是列表
        elif isinstance(link_data, list):
           links = []
           for link_dict in link_data:
               if "if" in link_dict:
                    links.append(ConditionalLink(target=link_dict["then"], condition=link_dict["if"]))
               else:
                    links.append(FallbackLink(target=link_dict["else"]))
           return links
        else:
            raise ValueError("Invalid next field")


class StartFlowStep(FlowStep):
    """
    流程开始步骤
    """
    type: FlowStepType = FlowStepType.START
    @classmethod
    def from_dict(cls, data: dict) -> "StartFlowStep":
        return cls(**FlowStep.base_fields(data))

class EndFlowStep(FlowStep):
    """
    流程结束步骤
    """
    type: FlowStepType = FlowStepType.END
    @classmethod
    def from_dict(cls, data: dict) -> "EndFlowStep":
        return cls(**FlowStep.base_fields(data))

class ActionFlowStep(FlowStep):
    """
    流程执行某一个动作步骤
    """
    type: FlowStepType = FlowStepType.ACTION

    action: str #动作名称 必填
    args:dict = {} #动作参数 选填
    @classmethod
    def from_dict(cls, data: dict) -> "ActionFlowStep":
        print("action")
        return cls(
            **FlowStep.base_fields(data),
            action=data["action"],
            args=data.get("args", {}))

class CollectFlowStep(FlowStep):
    """
    流程步骤：收集某个槽位信息
    """
    type: FlowStepType = FlowStepType.COLLECT

    slot_name: str #槽位名称，必填
    response: ResponseDefinition #槽位相关数据 必填
    @classmethod
    def from_dict(cls, data: dict) -> "CollectFlowStep":
        return cls(
            **FlowStep.base_fields(data),
            slot_name=data["slot_name"],
            response=ResponseDefinition(**data["response"]))


STEP_TYPE_TO_CLASS = {
    "start": StartFlowStep,
    "end": EndFlowStep,
    "action": ActionFlowStep,
    "collect": CollectFlowStep,
}

if __name__ == '__main__':
    obj = {
        "id": "start",
        "type": "action",
        "action": "action_lookup_logistics",
        "args":{
            "text":"一句话"
        },
        "next": [],
    }

    obj2 = FlowStep.from_dict(obj)
    print(obj2)