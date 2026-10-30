import time
from typing import List

from clarify.responder import ClarifyResponder
from domain.messages import UserMessage, ProcessResult, BotMessage, MessageType
from domain.state import DialogueState
from plan.models import ClarifyReason
from plan.turn_planner import TurnPlanner
from task.command.models import Command, SetSlotsCommand
from task.flow.flows import FlowsList
from task.flow.steps import CollectFlowStep
from task.handler import TaskHandler
from knowledge.registry import KnowledgeProviderRegistry
from knowledge.handler import KnowledgeHandler
from plan.turn_validator import TurnPlanValidator
from chitchat.handler import ChitChatHandler
async def get_dialogue_engine():
    return DialogueEngine()

class DialogueEngine:
    """
    对话引擎
    """

    def __init__(
            self,
            turn_planner: TurnPlanner,
            task_handler: TaskHandler,
            knowledge_handler : KnowledgeHandler,
            provider_registry: KnowledgeProviderRegistry,
            turn_planner_validator: TurnPlanValidator,
            clarify_responder: ClarifyResponder,
            chitchat_handler: ChitChatHandler,

    ) -> None:
        self.turn_planner = turn_planner
        self.task_handler = task_handler
        self.knowledge_handler = knowledge_handler
        self.clarify_responder = clarify_responder
        self.chitchat_handler = chitchat_handler
        self.turn_planner_validator = turn_planner_validator
        self.provider_registry = provider_registry


    async def process_message(self,dialog_state:DialogueState,user_message:UserMessage) -> ProcessResult:

        #1.准备会话（session）
        self._prepare_session(dialog_state)

        #2.开启本轮会话（turn）
        self._begin_turn(dialog_state,user_message)

        #3.判断消息类型（LLM）
        if user_message.type is MessageType.TEXT:
            #3.1文本消息
            messages = await self._handle_text_message(dialog_state)
        else:
            #3.2非文本消息
            dialog_state.set_focused_object(user_message.object)
            messages = await self._handle_object_message(
                message=user_message,
                state=dialog_state,
            )

        #4.提交本轮消息
        #4.1将消息添加到待提交的轮会话中
        dialog_state.pending_turn.bot_message.extend(messages)
        #4.2提交本轮会话
        dialog_state.commit_pending_turn()

        #5.将消息返回
        return ProcessResult(
            sender_id = user_message.sender_id,
            message_id = user_message.message_id,
            messages = messages
        )

    def _prepare_session(self, dialog_state:DialogueState):
        """
        准备会话
        :param dialog_state:
        :return:
        """
        #1.获取当前会话
        session = dialog_state.current_session()

        #2.如果当前会话不存在，则创建
        if session is None:
            dialog_state.start_session()
            return

        #3.如果当前会话存在，则判断超时时间
        now = time.time()
        # 判断会话是否超时
        if now - session.last_activity_at > 60 * 60 :#1小时
            # 关闭会话
            dialog_state.close_current_session()
            # 重置会话状态
            dialog_state.reset_runtime_state_for_new_session()
            # 创建新会话
            dialog_state.start_session()
        else:
            session.last_activity_at = now #续期

    def _begin_turn(self, dialog_state: DialogueState, user_message: UserMessage):
        """
        开始本轮会话
        :param dialog_state:
        :param user_message:
        :return:
        """
        dialog_state.begin_turn(user_message)

    async def _handle_text_message(self, dialog_state: DialogueState) -> List[BotMessage]:
        """
        处理文本消息
        :param dialog_state: 会话状态
        :return: 机器人消息列表
        """
        #1. 调用LLM 生成本轮的计划（由TurnPlanner 生成 TurnPlan）
        turn_plan = await self.turn_planner.predict(
            state=dialog_state,
            flows_list=self.task_handler.flows,
            intents=self.knowledge_handler.knowledge_intents,
        )

        #2. 幻觉校验 合法性校验
        validation_result = self.turn_planner_validator.validate(
            state=dialog_state,
            turn_plan=turn_plan,
            flow_list=self.task_handler.flows,
            intents=self.knowledge_handler.knowledge_intents,
        )
        #判断校验是否通过
        if not validation_result.valid:
            # 校验不通过：返回澄清信息
            return await self.clarify_responder.respond(dialog_state, validation_result.reason)

        #3. 按照轨道进行分发
        if turn_plan.task is not None:
            #3.1 业务任务
            messages = await self.task_handler.handle(commands = turn_plan.task.commands, state = dialog_state)
            return messages
        elif turn_plan.knowledge is not None:
            #3.2 知识库查询
            return await self.knowledge_handler.handle(intents=turn_plan.knowledge.intents, state=dialog_state)
        else :
            #3.3 闲聊
            return await self.chitchat_handler.handle(state= dialog_state)
        return []

    async def _handle_object_message(
            self,
            message: UserMessage,
            state: DialogueState,
    ) -> list[BotMessage]:
        """
        处理对象消息
        :param message:
        :param state:
        :return:
        """

        # 1. 将对象解析成command(SetSlotsCommand)
        commands = self._resolve_object_commands(
            message=message,
            state=state,
            flows=self.task_handler.flows,
        )

        # 2. 判断command是否已经存在(流程的步骤刚好需要你点击的卡片)
        if commands:
            # 场景 A:对象能填当前槽 → 转成命令,推进流程
            return await self.task_handler.handle(commands=commands, state=state)

        # 有流程，没有匹配到 slot
        # 如果用户正在一个流程中,不打断,让流程继续。
        if state.active_task is not None:
            # 场景 C:在流程里但槽不匹配 → 或者槽已填充 ->不打断,空命令让流程继续
            return await self.task_handler.handle(commands=[], state=state)

        # 没有流程：
        # 场景 B:没有流程 → 澄清
        return await self.clarify_responder.respond(
            dialogue_state=state,
            reason=ClarifyReason.OBJECT_REQUIRES_INTENT
        )

    def _resolve_object_commands(self, message: UserMessage, state: DialogueState, flows: FlowsList) -> list[Command]:
        """
        将对象消息转成command
        :param message:
        :param state:
        :param flows:
        :return:
        """

        # 1.获取聚焦对象
        focused_object = message.object
        if focused_object is None:
            return [  ]

        # 2.获取聚焦对象的类型
        object_type = focused_object.type

        # 3.判断聚焦对象类型
        # 3.1 order
        if object_type == "order":
            # 如果当前流程中包含订单号的槽位信息，那么就组织搜集订单号的Command命令
            if self._flow_has_unfilled_collect_slot(state, flows, "order_number"):
                return [SetSlotsCommand(command= "set_slots", slots={"order_number": focused_object.id})]
            return []
        # 3.2 product
        if object_type == "product":
            # 如果当前流程中包含商品id的槽位信息，那么就组织搜集商品id的命令
            if self._flow_has_unfilled_collect_slot(state, flows, "product_id"):
                return  [SetSlotsCommand(command="set_slots",slots={"product_id": focused_object.id})]
            return []
        return []

    def _flow_has_unfilled_collect_slot(self, state: DialogueState, flows: FlowsList, slot_name: str):
        """
        判断当前流程中是否包含未填槽的搜集槽
        :param state:
        :param flows:
        :param slot_name:
        :return:如果没有填充内容则返回True，否则返回False
        """

        # 1.获取当前任务
        active_task = state.active_task

        # 2.判断当前任务是否存在
        if active_task is None:
            return False

        # 3.根据活跃任务的id获取流程
        flow_id = active_task.flow_id
        flow = flows.get_flow_by_id(flow_id)
        if flow is None:
            # flow不存在
            return False

        # 4.判断当前的流程中是否包含未填槽的搜集槽
        if active_task.slots.get(slot_name):
            return False

        # 5.遍历流程的步骤，查找是否有某个步骤需要收集的槽位
        for step in flow.steps:
            if isinstance(step,CollectFlowStep) and step.name == slot_name :
                return True

        return False
