from typing import Annotated, Literal
from pydantic import BaseModel, TypeAdapter, Field


class TaskContext(BaseModel):
    """
    业务任务流程上下文
    """
    flow_id: str #业务任务的流程id
    step_id: str | None = None #业务任务的步骤id
    slots: dict  = {} #业务任务的槽位信息

class SystemContext(BaseModel):
    """
    系统流程上下文（抽象基类，不参与联合类型）
    定义具体流程的通用属性
    """
    flow_id: str #业务任务的流程id
    step_id: str | None = None

class StartedSystemContext(SystemContext):
    """
    流程开始
    """
    started_flow_id: str = ""
    started_flow_name: str = ""
    #使用 Literal 限制 flow_id值，作为 Discriminated Union 的区分字段
    flow_id: Literal["system_task_started"] = "system_task_started"

class InterruptedSystemContext(SystemContext):
    """
    流程中断
    """
    interrupted_flow_id: str = ""
    interrupted_flow_name: str = ""
    started_flow_id: str = ""
    started_flow_name: str = ""
    flow_id: Literal["system_task_interrupted"] = "system_task_interrupted"

class CanceledSystemContext(SystemContext):
    """
    流程取消
    """
    flow_id: Literal["system_task_canceled"] = "system_task_canceled"
    canceled_flow_id: str = ""
    canceled_flow_name: str = ""

class ResumedSystemContext(SystemContext):
    """
    流程恢复
    """
    resumed_flow_id: str = ""
    resumed_flow_name: str = ""
    flow_id: Literal["system_task_resumed"] = "system_task_resumed"

class CollectedSystemContext(SystemContext):
    """
    流程收集
    """
    flow_id: Literal["system_task_collected"] = "system_task_collected"
    slot_name: str = ""
    response: dict = {}

# 关键：Union 里不要包含 SystemContext 基类
SystemContextUnion = Annotated[
    StartedSystemContext |
    InterruptedSystemContext |
    CanceledSystemContext |
    ResumedSystemContext |
    CollectedSystemContext,
    Field(discriminator="flow_id")
]

system_context_adapter = TypeAdapter(SystemContextUnion)

if __name__ == '__main__':
    obj = StartedSystemContext(
        flow_id="123",
        step_id="456",
        started_flow_id="789",
        started_flow_name="test"
    )
    res = obj.model_dump(mode="json")
    obj2 = system_context_adapter.validate_python(res)
    print(res)
    print(obj2)