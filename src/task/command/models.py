from typing import Any

from pydantic import BaseModel


class Command(BaseModel):
    command: str

    #类型分发
    @classmethod
    def from_dict(cls, data: dict) -> "Command":
        clz = COMMAND_NAME_TO_CLASS[data["command"]]
        return clz(**data)

class StartFlowCommand(Command):
    flow: str

class SetSlotsCommand(Command):
    slots: dict[str,Any]

class CancelFlowCommand(Command):
    pass

class ResumeFlowCommand(Command):
    flow: str | None = None


COMMAND_NAME_TO_CLASS = {
    "start_flow": StartFlowCommand,
    "set_slots": SetSlotsCommand,
    "cancel_flow": CancelFlowCommand,
    "resume_flow": ResumeFlowCommand,
}

if __name__ == '__main__':
    dict_data1 = {"command":"start_flow","flow":"refund_request"}

    obj = Command.from_dict(dict_data1)

    print(obj)