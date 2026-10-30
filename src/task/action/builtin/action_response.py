from jinja2 import Template

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from domain.messages import BotMessage
from domain.state import DialogueState
from infrastructure.llm import llm
from prompts.history_builder import HistoryBuilder
from task.action.base import Action, ActionResult


class ActionResponse(Action):
    """
    给用户返回一句话：提示收集槽位信息
    """
    name = "action_response"
    async def run(self, state, action_kwargs):
        mode = action_kwargs.get("mode", "static")
        if mode == "static":
            text = action_kwargs["text"]
            rendered_text = self._render_text(text, state)

            return ActionResult(messages=[BotMessage(text=rendered_text)])
        elif mode == "rephrase":
            text = action_kwargs["text"]
            rendered_text = self._render_text(text, state)
            prompt_text = action_kwargs["prompt"]
            message = await self._call_llm(rendered_text, prompt_text,state)

            return ActionResult(messages=[BotMessage(text=message)])

        else:# generate
            prompt_text = action_kwargs["prompt"]
            message = await self._call_llm("", prompt_text, state)

            return ActionResult(messages=[BotMessage(text=message)])

    @staticmethod
    def _render_text(text: str, state:DialogueState) ->str:
        """
        将模板中的占位符替换成真实的值
        :param text:
        :param state:
        :return:
        """
        context = state.active_system_task or state.active_task

        return Template(text).render(
            slots=state.active_task.slots if state.active_task else {},
            context=context.model_dump() if context is not None else {},
        )

    @staticmethod
    async def _call_llm( rendered_text: str, prompt_text: str, state: DialogueState):
        """
        调用语言模型
        :param rendered_text:
        :param prompt_text:
        :param state:
        :return:
        """
        # 获取提示词模板
        prompt = PromptTemplate.from_template(template=prompt_text, template_format="jinja2")
        chain = prompt | llm | StrOutputParser()
        bot_message =  await chain.ainvoke({
            "history": HistoryBuilder.build(state.current_session().turns),
            "user_message": HistoryBuilder.render_user_message(state.pending_turn.user_message),
            "current_response": rendered_text
            }
        )

        return  bot_message