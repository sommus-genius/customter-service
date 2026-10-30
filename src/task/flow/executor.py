from domain.contexts import CollectedSystemContext
from domain.messages import BotMessage
from domain.state import DialogueState
from task.action.base import ActionResult
from task.action.runner import ActionRunner, ActionCall
from task.flow.flows import FlowsList
from task.flow.links import StaticLink, ConditionalLink, FallbackLink
from task.flow.steps import FlowStep, StartFlowStep, EndFlowStep, CollectFlowStep, ActionFlowStep


class FlowExecutor:
    """
    推进yml文件中定义的业务流程以及系统流程
    内存循环：负责流程的不断推进
    外层循环：负责执行action，如果action的类型是action_listen，则跳出外层循环
    """

    async def run_task(
            self,
            state: DialogueState,
            flows: FlowsList,
            action_runner: ActionRunner
    ) -> list[BotMessage]:
        messages :list[BotMessage] = []

        while True:
            # 1.推进流程的执行（step），当step的类型是action的时候从内存循环中退出
            action_call: ActionCall = self.advance_until_action(state,flows)

            # 2.当action_name是action_listen
            if action_call.action_name == "action_listen":
                break
            else:

                # 3.其他类型的action,则需要执行
                action_result: ActionResult = await action_runner.run(action_call,state)
                state.set_slots(action_result.slot_updates)
                messages.extend(action_result.messages)
        # 返回消息，等待下一轮用户的输入
        return messages

    def advance_until_action(self, state: DialogueState, flows: FlowsList) -> ActionCall:
        """
        进推流程的执行，直到遇到action为止
        :param state:
        :param flows:
        :return:
        """
        while True:

            # 1.获取当前任务的上下文对象
            current_active_task = state.current_active_task()

            # 2.如果当前没有任务，返回action_listen
            if current_active_task is None:
                return ActionCall(action_name="action_listen")

            # 3.获取当前流程对象
            flow = flows.get_flow_by_id(current_active_task.flow_id)

            # 4.获取当前步骤对象
            step = flow.get_step_by_id(current_active_task.step_id)

            # 5.运行当前的step
            action_call = self._run_step(state,step,flows)

            # 6.如果step的类型是action
            if action_call is not None:
                return action_call


    def _run_step(self, state: DialogueState, step: FlowStep, flows: FlowsList) -> ActionCall:
        """
        运行当前的step
        :param state:
        :param step:
        :param flows:
        :return:
        """
        if isinstance(step,StartFlowStep):

            return self._run_start_step(state, step)

        if isinstance(step,EndFlowStep):

            return self._run_end_step(state)

        if isinstance(step,CollectFlowStep):

            return self._run_collect_step(state, step, flows)

        if isinstance(step,ActionFlowStep):

            return self._run_action_step(state, step)

    def _run_start_step(self, state, step) -> None:
        """
        运行开始步骤
        :param state:
        :param step:
        :return:
        """
        # 1.推进下一步
        self._acvance_next_step(state,step)
        # 2.返回None,让内存循环继续进行流程的推进，不跳出
        return None

    def _acvance_next_step(self, state: DialogueState, step: FlowStep):
        # 1.寻找下一个步骤的step_id
        next_step_id = self._select_next_step(state,step)
        # 2.推进下一步
        state.current_active_task().step_id = next_step_id

    def _select_next_step(self, state: DialogueState, step: FlowStep):
        for link in step.next:
            if isinstance(link,StaticLink):
                return link.target
            if isinstance(link,ConditionalLink):

                if self._eval_condition(state, link.condition):
                    return link.target

            if isinstance(link,FallbackLink):
                return link.target
            
        return "没有下一步"

    @staticmethod
    def _eval_condition(self, state: DialogueState, condition: str) -> bool:
        data = {
            "context": state.current_active_task().model_dump(mode="json"),
            "slots": state.active_task.slots
        }

        return eval(condition,{'_builtins_':None},data)

    @staticmethod
    def _run_end_step( state: DialogueState) ->None:

        if state.active_system_task is not None:
            state.end_active_system_task()
        else:
            state.end_active_task()

        return None

    def _run_action_step(self, state: DialogueState, step: ActionFlowStep):

        # 1.推进下一步
        self._acvance_next_step(state,step)
        action_call = self._build_action_call(state,step)

        return action_call

    @staticmethod
    def _build_action_call(state: DialogueState, step: ActionFlowStep) -> ActionCall:

        action_name = step.action
        action_kwargs = step.args

        if isinstance(action_kwargs, str):

            action_kwargs = state.active_system_task.model_dump(mode="json")[action_kwargs.split(".")[1]]

        return ActionCall(action_name = action_name,action_kwargs = action_kwargs)

    def _run_collect_step(
            self,
            state: DialogueState,
            step: CollectFlowStep,
            flows: FlowsList,
    ):

        # 1.尝试自动补槽
        self._try_to_fill_collect_slot_focused_object(state,step)

        # 2.判断槽位是否已经填上
        slot_value = state.active_task.slots.get(step.slot_name)
        if slot_value is not None and slot_value != "":

            #3.推进下一步
            self._acvance_next_step(state,step)
            return None
        else:
            # 槽位信息没有添加，则添加系统过场
            state.start_active_system_task(CollectedSystemContext(
                flow_id="system_collect_information",
                step_id= flows.get_flow_by_id("system_collect_information").start_step().id,
                slot_name=step.slot_name,
                response=step.response.model_dump(mode="json")
            ))
        return None

    def _try_to_fill_collect_slot_focused_object(self, state: DialogueState, step: CollectFlowStep):

        if state.focused_object is None:
            return None

        if step.slot_name == "order_number" and state.focused_object.type == "order":
            state.set_slots({step.slot_name:state.focused_object.id})

        if step.slot_name == "product_id" and state.focused_object.type == "product":
            state.set_slots({step.slot_name:state.focused_object.id})

