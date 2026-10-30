import time

import uuid
from typing import Any

from pydantic import BaseModel

from domain.contexts import SystemContextUnion, TaskContext
from domain.messages import UserMessage, BotMessage, FocuseObject


class Turn(BaseModel):
    """
    本轮对话的对象
    """
    turn_id: str #轮次唯一标识，使用UUID
    user_message: UserMessage #这一轮用户说的那一句话
    bot_message: list[BotMessage] #这一轮系统给出的所有回复


class Session(BaseModel):
    """
    会话信息
    """
    session_id: str  # 会话唯一标识，使用UUID
    started_at: float #会话开始的时间戳
    last_activity_at: float #会话最后活跃的时间戳
    closed_at: float | None = None #会话结束的时间戳，如果会话没有结束则为None
    turns: list[Turn]  # 这一轮对话的所有轮次

class DialogueState(BaseModel):
    """
    对话状态
    """
    sender_id: str #用户唯一标识
    active_task: TaskContext | None = None #当前活跃的业务任务
    paused_tasks: list[TaskContext] = [] #被挂起的任务列表
    active_system_task: SystemContextUnion | None = None #当前执行的系统流程
    focused_object: FocuseObject | None = None #用户当前聚焦的订单/商品
    sessions:list[Session] = [] #历史会话列表
    current_session_id: str | None = None #当前活跃会话的ID
    pending_turn: Turn | None = None #正在处理中的轮次

    #------------------任务相关------------------
    def start_active_task(self,active_task: TaskContext):
        """
         把传进来的任务设为当前活跃任务
         调用时机：当 TurnPlanner 判断用户发起一个新任务时
        :param active_task:
        :return:
        """
        self.active_task = active_task

    def end_active_task(self):
        """
        结束当前活跃任务
        调用时机：当业务任务流程跑到 end步骤时
        :return:
        """
        self.active_task = None

    def cancel_active_task(self):
        """
        取消业务任务
        把活跃任务和当前系统过场都清空
        调用时机：用户主动说：”算了不退了“这类取消意图时
        :return:
        """
        self.active_task = None
        self.active_system_task = None

    def interrupted_active_task(self):
        """
        中断当前活跃任务
        调用时机：当用户说了一些和当前任务无关的话时
        :return:
        """
        if self.active_task is not None:
            self.paused_tasks.append(self.active_task)
        self.active_task = None
        self.active_system_task = None

    def resumed_active_task(self,flow_id: str | None = None) -> bool:
        """
        恢复中断的活跃任务:流程ID
        如果用户没有明确指定需要回复的具体任务，那么 flow_id = None
        如果用户明确指定需要恢复的具体任务
            则按flow_id 再挂起列表里找一个任务，恢复为活跃任务，并从挂起列表中移除
        调用时机：用户说”继续刚才的退款“这类意图时
        注意：任务被恢复时，step_id 和 slots都还在，所以可以从挂起前的位置接着跑，不用从头来
        :param flow_id:
        :return:
        """
        # 1.栈中是否存在可恢复的任务
        if not self.paused_tasks:
            return False

        # 2.恢复最近的任务
        if not flow_id:
            self.active_task = self.paused_tasks.pop()
            return True

        # 3.恢复指定任务
        for i, paused_task in enumerate(self.paused_tasks):
            if paused_task.flow_id == flow_id:
                self.active_task = paused_task
                del self.paused_tasks[i]
                return True

        # 4.没有找到指定任务，保持当前状态
        return False

    def start_active_system_task(self,active_system_task: SystemContextUnion):
        """
        开启系统流程
        调用时机：每当系统要插入系统流程（任务开始、打断、取消、恢复、收集槽位）时
        :param active_system_task:
        :return:
        """
        self.active_system_task = active_system_task


    def end_active_system_task(self):
        """
         结束当前系统流程
         调用时机：每当系统流程跑到 end 步骤时
         :return:
         """
        self.active_system_task = None

    def current_active_task(self):
        """
        返回当前正在执行的任务（系统流程、业务任务）
        先获取系统流程 如果获取不到 获取业务任务
        - 如果有系统流程，先返回系统流程
        - 否则返回业务任务

        为什么系统流程优先？
        因为系统流程往往是要插播一句过场白，必须先说完，然后才能让位给业务任务继续
        :return:
        """
        return self.active_system_task or self.active_task

    #------------------槽位相关-------------------
    def set_slots(self,slots:dict[str, Any]):
        """
        设置槽位
        把传进来的dict 合并到当前活跃任务的slots
        :param slots:
        :return:
        """
        self.active_task.slots.update(slots)

    def remove_slot(self,slot_name: str):
        """
        移除槽位
        从当前活跃任务的slots中移除指定槽位
        :param slot_name: 槽位名称
        :param slot_name:
        :return:
        """
        self.active_task.slots.pop(slot_name)

    #----------------Session相关--------------------
    def current_session(self) ->Session | None:
        """
        获取当前会话对象
        根据 current_session_id 获取当前会话对象
        :return: 当前会话对象，如果当前会话不存在则返回None
        """
        for session in self.sessions:
            if session.session_id == self.current_session_id :
                return session

        return None

    def start_session(self):
        """
        开启新会话
        创建一个新的Session，加进sessions列表，并把他设为当前会话
        :return:
        """
        if self.current_session() is None:
            # 开启新会话
            now = time.time()
            session_id = str(uuid.uuid4())
            session = Session(
                session_id=session_id,
                started_at=now,
                last_activity_at=now,
                closed_at=None,
                turns=[]
            )

            # 添加会话到会话列表
            self.sessions.append(session)
            # 设置当前会话
            self.current_session_id = session_id


    def close_current_session(self):
        """
        结束当前会话
        给当前会话打上关闭时间戳，表示会话结束，再把 current_session_id置空
        :return:
        """
        if self.current_session() is None:
            #设置关闭时间，关闭当前会话
            self.current_session().closed_at = time.time()
            #清空会话状态中的session_id
            self.current_session_id = None


    def reset_runtime_state_for_new_session(self):
        """
        重置会话状态，为新会话做准备
        session会话超时新绘画开始前的“清理工作”
        注意：
        -它只清运行时字段：当前任务、挂起任务、系统过长、聚焦对象
        -它不清sessions：会话历史记录要保留
        :return:
        """
        self.active_task = None
        self.active_system_task = None
        self.paused_tasks = []
        self.focused_object = None
        self.pending_turn = None
        self.current_session_id = None

    #-----------------turn相关------------------
    def begin_turn(self,message: UserMessage):
        """
        开始一轮对话
        收到用户消息后，把他装进到一个新的turn对象
        先放到 pending_turn,而不是直接进session
        :param message:
        :return:
        """
        if self.current_session():
            self.pending_turn = Turn(
                turn_id=str(uuid.uuid4()),
                user_message=message,
                bot_message=[]
            )

    def commit_pending_turn(self):
        """
        提交一个turn
        本轮处理完成（用户消息+系统回复）后
        把pending_turn加到当前会话的turns列表里，再把pending_turn置空
        :return:
        """
        if self.current_session():
            self.current_session().turns.append(self.pending_turn)
            self.pending_turn = None

    #----------------FocusedObject相关--------------------
    def set_focused_object(self,focused_object:FocuseObject):
        """
        设置聚焦对象
        调用时机：
        用户发的不是文本而是一条对象消息时，例如前端点了订单卡片
        需要把这个对象设为当前关注的对象
        :param focused_object:
        :return:
        """
        self.focused_object = focused_object
