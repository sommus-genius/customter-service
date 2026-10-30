from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import load_prompt, PromptTemplate

from domain.messages import UserMessage, BotMessage
from domain.state import Turn
from infrastructure.llm import llm
from prompts.history_builder import HistoryBuilder


class ChitChatResponder:

    async def respond(self,
                      user_message: UserMessage,
                      recent_turns: list[Turn]):

        user_message = HistoryBuilder._render_user_message(user_message)
        history = HistoryBuilder.build(recent_turns)

        prompt_text = load_prompt("chitchat_respond")
        prompt = PromptTemplate.from_template(prompt_text, template_format="jinja2")
        chain = prompt | llm | StrOutputParser()
        response = await chain.ainvoke({
            "user_message": user_message,
            "history": history,
        })
        return [BotMessage(text=response)]