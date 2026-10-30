from enum import Enum

from pydantic import BaseModel

from task.command.models import Command


class TaskTurnPlan(BaseModel):
    commands: list[Command] = [] # 命令

    @classmethod
    def from_dict(cls, data: dict) -> "TaskTurnPlan":
        return cls(commands=[Command.from_dict(command_data) for command_data in data["commands"]])

class KnowledgeTurnPlan(BaseModel):
    intents: list[str] = [] #意图
    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeTurnPlan":
        return cls(intents=data["intents"])

class ChitchatTurnPlan(BaseModel):
    chitchat: list[str]
    @classmethod
    def from_dict(cls, data: dict) -> "ChitchatTurnPlan":
        return cls(chitchat=data["chitchat"])


class TurnPlan(BaseModel):
    task: TaskTurnPlan | None = None
    knowledge: KnowledgeTurnPlan | None = None
    chitchat: ChitchatTurnPlan | None = None

    @classmethod
    def from_dict(cls,data:dict) -> "TurnPlan":
        return cls(
            task=TaskTurnPlan.from_dict(data["task"]) if data["task"] else None,
            knowledge=KnowledgeTurnPlan.from_dict(data["knowledge"]) if data["knowledge"] else None,
            chitchat=ChitchatTurnPlan.from_dict(data["chitchat"]) if data["chitchat"] else None
        )

class ClarifyReason(str,Enum):
    MISSING_TRACK = "missing_track"
    MULTIPLE_TRACKS = "multiple_tracks"
    MISSING_TASK_COMMANDS = "missing_task_commands"
    MISSING_KNOWLEDGE_INTENT = "missing_knowledge_intent"
    MISSING_FOCUSED_OBJECT = "missing_focused_object"
    OBJECT_REQUIRES_INTENT = "object_requires_intent"
    INVALID_TASK_COMMANDS = "invalid_task_commands"
    MULTIPLE_TRACKS_FLOWS = "multiple_tracks_flows"
    UNKNOWN_TASK_FLOW = "unknown_task_flow"
    UNKNOWN_KNOWLEDGE_FLOW = "unknown_knowledge_flow"
    UNKNOWN_CHITCHAT_FLOW = "unknown_chitchat_flow"
    UNKNOWN_FLOW = "unknown_flow"


class TurnPlanValidationResult(BaseModel):
    valid: bool #是否有效
    reason: ClarifyReason | None = None #无效时的原因