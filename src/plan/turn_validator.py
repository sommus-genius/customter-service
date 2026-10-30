from typing import Dict

from domain.state import DialogueState
from knowledge.intents import KnowledgeIntent
from plan.models import TurnPlan, TurnPlanValidationResult, ClarifyReason
from task.command.models import StartFlowCommand, SetSlotsCommand, CancelFlowCommand, ResumeFlowCommand
from task.flow.flows import FlowsList


class TurnPlanValidator:
    """
    意图验证器
    作用：根据意图分析结果，对意图进行校验
    """

    def validate(
            self,
            state: DialogueState,
            turn_plan: TurnPlan,
            flow_list: FlowsList,
            intents: Dict[str, KnowledgeIntent]
    ) -> TurnPlanValidationResult:
        """
        校验 turn_plan 是否符合要求
        :param state:
        :param turn_plan:
        :param flow_list:
        :param intents:
        :return:
        """
        active_tracks = self._active_tracks(turn_plan)

        # 1. 是否有命中轨道
        if not active_tracks:
            return self._reject(ClarifyReason.MISSING_TRACK)

        # 2. 是否有多个轨道
        if len(active_tracks) > 1:
            return self._reject(ClarifyReason.MULTIPLE_TRACKS)

        # 3.命中一个轨道
        active_track = active_tracks[0]

        # 4.判断轨道是哪一个
        # 流程分支
        if active_track == "task":
            return self._validate_task(turn_plan, flow_list)

        # 知识查询分支
        elif active_track == "knowledge":
            return self._validate_knowledge(
                state=state,
                turn_plan=turn_plan,
                intents=intents,
            )

        # 闲聊分支
        elif active_track == "chitchat":
            return self._validate_chitchat(state, turn_plan, flow_list, intents)


    def _active_tracks(self, turn_plan: TurnPlan) -> list[str]:

        active_tracks: list[str] = []

        if turn_plan.task is not None:
            active_tracks.append("task") #task：轨道的名字

        if turn_plan.knowledge is not None:
            active_tracks.append("knowledge") #knowledge：轨道的名字

        if turn_plan.chitchat is not None:
            active_tracks.append("chitchat") #chitchat：轨道的名字

        return active_tracks

    def _reject(self, reason: ClarifyReason):
        return TurnPlanValidationResult(valid=False, reason=reason)

    def _validate_task(self, turn_plan: TurnPlan, flow_list: FlowsList) -> TurnPlanValidationResult:

        task_plan = turn_plan.task

        # 第一重校验： commands不能为空
        if task_plan is None or not task_plan.commands:
            return self._reject(ClarifyReason.MISSING_TASK_COMMANDS)

        # 第二重校验： commands中的每个command都必须在flow_list中存在
        allowed = (StartFlowCommand,SetSlotsCommand,CancelFlowCommand,ResumeFlowCommand)
        if not all(isinstance(command, allowed) for command in task_plan.commands):
            return self._reject(ClarifyReason.INVALID_TASK_COMMANDS)

        # 第三重校验： 不能一次开启多个流程（有多个 start_flow)
        start_commands = [command for command in task_plan.commands if isinstance(command, StartFlowCommand)]
        if len(start_commands) > 1:
            return self._reject(ClarifyReason.MULTIPLE_TRACKS_FLOWS)

        # 第四重校验：新开的流程名称必须真实存在
        if start_commands:
            if flow_list.get_flow_by_id(start_commands[0].flow) is None:
                return self._reject(ClarifyReason.UNKNOWN_TASK_FLOW)

        return TurnPlanValidationResult(valid=True)

    def _validate_knowledge(
            self,
            state: DialogueState,
            turn_plan: TurnPlan,
            intents: Dict[str, KnowledgeIntent]
    ) -> TurnPlanValidationResult:

        # 第一重校验： knowledge_plan不能为空
        knowledge_plan = turn_plan.knowledge
        if knowledge_plan is None or not knowledge_plan.intents:
            return self._reject(ClarifyReason.MISSING_KNOWLEDGE_INTENT)

        # 第二重校验： intent必须真实存在
        # 获取当前聚焦对象
        focused_object = state.focused_object
        # 遍历大模型分析出来的用户意图
        for intent in knowledge_plan.intents:
            # 根据用户意图 获取intents字典中的意图元数据
            intent_meta = intents[intent]
            # 获取意图元数据中的required_object类型
            required_object = intent_meta.requires_object
            # 如果有对象类型：说明是api检索
            if required_object is not None:
                # 判断用户意图是否与聚焦对象匹配
                if focused_object is None or focused_object.type != required_object:
                    # 返回校验错误的结果，需要用户澄清
                    return self._reject(ClarifyReason.MISSING_FOCUSED_OBJECT)

        return TurnPlanValidationResult(valid=True)
