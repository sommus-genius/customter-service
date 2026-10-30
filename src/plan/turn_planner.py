import json
from dataclasses import asdict
from typing import Dict

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

from domain.contexts import TaskContext
from domain.state import DialogueState
from infrastructure.llm import llm
from plan.models import TurnPlan
from prompts.history_builder import HistoryBuilder
from prompts.loader import load_prompt
from task.flow.flows import FlowsList
from plan.models import TurnPlan, ChitchatTurnPlan
from knowledge.intents import KnowledgeIntent
class TurnPlanner:
    """
    意图分析器
    作用：根据任务自然语言调用 LLM分析轨道类型
    """

    async def predict(self,
                      state: DialogueState,
                      flows_list: FlowsList,
                      intents: Dict[str, KnowledgeIntent]
                      ) -> TurnPlan:
        """

        :param state:
        :param flows:
        :return:
        """
        # 1. 构建提示词
        inputs_prompt = self._build_prompt_inputs(state,flows_list,intents)
        # 2.调用LLM
        turn_plan = await self._predict_from_prompt_inputs(inputs_prompt)


        # 3. 返回TurnPlan
        return  turn_plan

    def _build_prompt_inputs(self, state: DialogueState, flows_list: FlowsList, intents: Dict[str, KnowledgeIntent]):
        """
        构建提示词
        :param state: 对话状态
        :param flows_list: 任务流列表
        :return: 提示词
        """
        # 1.用户消息
        user_message = HistoryBuilder._render_user_message(state.pending_turn.user_message)
        # 2.历史对话
        current_conversation = HistoryBuilder.build(state.current_session().turns[-10:])
        # 3.当前激活的任务
        active_task_json = json.dumps(state.active_task.model_dump(mode="json"), ensure_ascii=False) if state.active_task is not None else None
        # 4.中断的任务
        interrupted_task_json = json.dumps([paused.model_dump(mode="json") for paused in state.paused_tasks], ensure_ascii=False)
        # 5.聚焦对象
        focused_object_json = json.dumps(state.focused_object.model_dump(mode="json"), ensure_ascii=False) if state.focused_object is not None else None
        # 6.flows
        available_flows_json = json.dumps(
            {"flows":[{k: v for k, v in flow.model_dump(mode="json").items() if k != "steps"} for flow in flows_list.flows]},
            ensure_ascii=False
        )
        #7.通过提前定义的意图字典组装意图字典列表
        knowledge_intents_json = json.dumps([{"id": intent.id, "description": intent.description} for intent in intents.values()], ensure_ascii=False) if intents else "[]"

        return {
            "user_message": user_message,
            "current_conversation": current_conversation,
            "active_task_json": active_task_json,
            "interrupted_tasks_json": interrupted_task_json,
            "focused_object_json": focused_object_json,
            "available_flows_json": available_flows_json,
            "knowledge_intents_json": knowledge_intents_json
        }
    async def _predict_from_prompt_inputs(self, inputs_prompt) -> TurnPlan:
        """
        从提示词中预测轨道类型
        :param inputs_prompt: 提示词
        :return: 轨道类型
        """
        # 1.加载提示词模板
        prompt_template_text = load_prompt("turn_plan")
        prompt_template = PromptTemplate.from_template(template=prompt_template_text, template_format="jinja2")
        chain = prompt_template | llm | JsonOutputParser()

        # 2.使用inputs_prompt渲染提示词模板,调用模型生成结果
        llm_response_dict: Dict[str, str] = await chain.ainvoke(inputs_prompt)

        # 3.将结果转成TurnPlan对象
        return TurnPlan.from_dict(llm_response_dict)

if __name__ == '__main__':
    active_task = TaskContext(
        flow_id="test_flow_id",
        step_id="test_step_id",
        slots={"test_slot": "test_value"}
    )

    dict_data = active_task.model_dump(mode="json")
    print(dict_data)