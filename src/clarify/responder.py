from typing import List

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from domain.messages import BotMessage
from domain.state import DialogueState
from infrastructure.llm import llm
from plan.models import ClarifyReason
from prompts.history_builder import HistoryBuilder
from prompts.loader import load_prompt


class ClarifyResponder:

    async def respond(self, dialogue_state: DialogueState, reason: ClarifyReason) -> List[BotMessage]:
        """
        生成澄清回复
        步骤1：按照返回码的规则生成基础回复
        步骤2：根据提示词润色回复
        :param dialogue_state: 对话状态
        :param reason: 澄清原因
        :return: AI消息
        """
        # 步骤1：按照返回码的规则生成基础回复
        base_message = self.build_clarify_message(reason, dialogue_state)
        # 获取用户消息
        user_message = dialogue_state.pending_turn.user_message
        # 获取用户消息字符串
        user_message_str = HistoryBuilder._render_user_message(user_message)
        # 获取聚焦对象JSON
        focused_object_json = dialogue_state.focused_object.model_dump_json() if dialogue_state.focused_object is not None else None
        # 获取对话历史
        conversation_history = HistoryBuilder.build(
            dialogue_state.current_session().turns[-10:]
        )
        # 加载提示词
        prompt = load_prompt("clarify_respond")
        # 加载提示词模板
        prompt_template = PromptTemplate.from_template(template=prompt, template_format="jinja2")

        chain = prompt_template | llm | StrOutputParser()
        rewritten =  await chain.ainvoke({
            "user_message": user_message_str,
            "history": conversation_history,
            "focused_object": focused_object_json,
            "clarify_message": base_message,
            "reason": reason.value
        })
        # 返回机器人消息
        return [BotMessage(text=rewritten)]

    def build_clarify_message(
            self,
            reason: ClarifyReason,
            state: DialogueState,
    ) -> str:
        if reason is ClarifyReason.MULTIPLE_TRACKS:
            return "你这次同时提到了多个方向。我们先处理一个，你想先办业务还是先咨询信息呢？"

        if reason is ClarifyReason.MISSING_FOCUSED_OBJECT:
            return "请先发送你想咨询的对象，我再继续帮你看。"

        if reason is ClarifyReason.MISSING_KNOWLEDGE_INTENT:
            return "你是想了解商品信息、订单信息，还是售后配送规则呢？"

        if reason is ClarifyReason.MISSING_TRACK:
            return "你是想先处理业务问题，还是先咨询信息呢？"

        if reason is ClarifyReason.MISSING_TASK_COMMANDS:
            return "你这次是想办理什么业务呢？比如查订单、查物流，或者申请退款。"

        if reason is ClarifyReason.OBJECT_REQUIRES_INTENT:
            focused_object = state.focused_object
            if focused_object is not None and focused_object.type == "order":
                return "我已经收到这个订单了。你想查订单状态、查物流，还是申请退款呢？"
            if focused_object is not None and focused_object.type == "product":
                return "我已经收到这个商品了。你想了解它的商品信息、发货情况，还是售后相关问题呢？"

        return "我还需要再确认一下你的意思，你可以换个更具体的说法告诉我。"



