from pydantic import BaseModel

from task.flow.steps import FlowStep, StartFlowStep
from typing import List, Dict

class FlowSlot(BaseModel):
    """
    槽位
    """
    name: str #槽位的名字
    type: str = "any" #槽位的类型
    label: str = "" #槽位的标签
    description: str = "" #槽位的描述


class Flow(BaseModel):
    """
    流程
    """
    id: str #流程的id
    name: str | None = None #流程的名字
    description: str = "" #流程的描述
    steps: list[FlowStep] = [] #流程的步骤
    slots: list[FlowSlot] = [] #流程的槽位

    def start_step(self) -> FlowStep | None:
        """
        找到流程的开始节点
        :return:
        """
        for step in self.steps:
            if isinstance(step, StartFlowStep) :
                return step
        return None

    def get_step_by_id(self, step_id: str) -> FlowStep | None:
        """
        根据id获取步骤
        :param step_id:
        :return:
        """
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

class FlowsList(BaseModel):
    """
    流程列表
    """
    flows: List[Flow] = []
    slots: Dict[str, FlowSlot] = {}

    def get_flow_by_id(self, flow_id: str) -> Flow | None:
        """
        根据流程ID获取流程
        :param flow_id:
        :return:
        """
        for flow in self.flows:
            if flow.id == flow_id:
                return flow
        return None