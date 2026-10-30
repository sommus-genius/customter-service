from domain.contexts import (
    CanceledSystemContext, InterruptedSystemContext, ResumedSystemContext,
    StartedSystemContext, TaskContext,
)
from domain.state import DialogueState
from task.command.models import (
    Command, StartFlowCommand, SetSlotsCommand, CancelFlowCommand, ResumeFlowCommand,
)
from task.flow.flows import FlowsList


class CommandProcessor:
    """处理命令，更新业务任务及系统过场状态。"""

    def run(self, commands: list[Command], state: DialogueState, flows: FlowsList):
        for command in commands:
            self._apply_command(command, state, flows)

    def _apply_command(self, command: Command, state: DialogueState, flows: FlowsList):
        if isinstance(command, StartFlowCommand):
            self._handle_start_flow(command, state, flows)
        elif isinstance(command, SetSlotsCommand):
            if state.active_task is not None:
                state.set_slots(command.slots)
        elif isinstance(command, CancelFlowCommand):
            self._handle_cancel_flow(state, flows)
        elif isinstance(command, ResumeFlowCommand):
            self._handle_resume_flow(command, state, flows)
        else:
            raise ValueError(f"不支持的命令：{command.command}")

    def _handle_start_flow(self, command: StartFlowCommand, state: DialogueState, flows: FlowsList):
        if command.flow.startswith("system_"):
            raise ValueError(f"不允许直接启动系统流程：{command.flow}")
        start_step = self._start_step(command.flow, flows)
        active_task = state.active_task
        if active_task is not None and active_task.flow_id == command.flow:
            return

        # 先检查过场配置，再变更任务，避免配置错误时丢失当前状态。
        resumed = any(task.flow_id == command.flow for task in state.paused_tasks)
        system_flow_id = (
            "system_task_interrupted" if active_task is not None
            else "system_task_resumed" if resumed else "system_task_started"
        )
        self._start_step(system_flow_id, flows)
        state.end_active_system_task()
        if active_task is not None:
            state.interrupted_active_task()
        if not state.resumed_active_task(command.flow):
            state.start_active_task(TaskContext(flow_id=command.flow, step_id=start_step.id))

        flow_name = self._readable_flow_name(command.flow, flows)
        if active_task is not None:
            self._active_interrupted_system_flow(
                state, flows, active_task.flow_id,
                self._readable_flow_name(active_task.flow_id, flows), command.flow, flow_name,
            )
        elif resumed:
            self._active_resumed_system_flow(state, flows, command.flow, flow_name)
        else:
            self._active_start_system_flow(state, flows, command.flow, flow_name)

    def _handle_cancel_flow(self, state: DialogueState, flows: FlowsList):
        active_task = state.active_task
        if active_task is None:
            return
        self._start_step("system_task_canceled", flows)
        state.cancel_active_task()
        self._active_canceled_system_flow(
            state, flows, active_task.flow_id,
            self._readable_flow_name(active_task.flow_id, flows),
        )

    def _handle_resume_flow(self, command: ResumeFlowCommand, state: DialogueState, flows: FlowsList):
        if command.flow is not None:
            if command.flow.startswith("system_"):
                raise ValueError(f"不允许直接恢复系统流程：{command.flow}")
            if flows.get_flow_by_id(command.flow) is None:
                raise ValueError(f"流程不存在：{command.flow}")
            target_flow_id = command.flow
        else:
            if not state.paused_tasks:
                return
            target_flow_id = state.paused_tasks[-1].flow_id

        active_task = state.active_task
        if active_task is not None and active_task.flow_id == target_flow_id:
            return
        # 指定任务不在暂停栈时，不打断当前任务，也不恢复其他任务。
        if not any(task.flow_id == target_flow_id for task in state.paused_tasks):
            return
        if flows.get_flow_by_id(target_flow_id) is None:
            raise ValueError(f"流程不存在：{target_flow_id}")
        self._start_step(
            "system_task_interrupted" if active_task is not None else "system_task_resumed",
            flows,
        )
        if active_task is not None:
            state.interrupted_active_task()
        state.resumed_active_task(target_flow_id)
        target_name = self._readable_flow_name(target_flow_id, flows)
        if active_task is not None:
            self._active_interrupted_system_flow(
                state, flows, active_task.flow_id,
                self._readable_flow_name(active_task.flow_id, flows), target_flow_id, target_name,
            )
        else:
            self._active_resumed_system_flow(state, flows, target_flow_id, target_name)

    @staticmethod
    def _readable_flow_name(flow_id: str, flows: FlowsList) -> str:
        flow = flows.get_flow_by_id(flow_id)
        return (flow.name or flow_id) if flow is not None else flow_id

    @staticmethod
    def _start_step(flow_id: str, flows: FlowsList):
        flow = flows.get_flow_by_id(flow_id)
        if flow is None:
            raise ValueError(f"流程不存在：{flow_id}")
        step = flow.start_step()
        if step is None:
            raise ValueError(f"流程缺少开始步骤：{flow_id}")
        return step

    @staticmethod
    def _active_start_system_flow(state, flows, started_flow_id, started_flow_name):
        step = CommandProcessor._start_step("system_task_started", flows)
        state.start_active_system_task(StartedSystemContext(
            step_id=step.id, started_flow_id=started_flow_id, started_flow_name=started_flow_name,
        ))

    @staticmethod
    def _active_interrupted_system_flow(
        state, flows, interrupted_flow_id, interrupted_flow_name, started_flow_id, started_flow_name,
    ):
        step = CommandProcessor._start_step("system_task_interrupted", flows)
        state.start_active_system_task(InterruptedSystemContext(
            step_id=step.id, interrupted_flow_id=interrupted_flow_id,
            interrupted_flow_name=interrupted_flow_name,
            started_flow_id=started_flow_id, started_flow_name=started_flow_name,
        ))

    @staticmethod
    def _active_resumed_system_flow(state, flows, resumed_flow_id, resumed_flow_name):
        step = CommandProcessor._start_step("system_task_resumed", flows)
        state.start_active_system_task(ResumedSystemContext(
            step_id=step.id, resumed_flow_id=resumed_flow_id, resumed_flow_name=resumed_flow_name,
        ))

    @staticmethod
    def _active_canceled_system_flow(state, flows, canceled_flow_id, canceled_flow_name):
        step = CommandProcessor._start_step("system_task_canceled", flows)
        state.start_active_system_task(CanceledSystemContext(
            step_id=step.id, canceled_flow_id=canceled_flow_id, canceled_flow_name=canceled_flow_name,
        ))
