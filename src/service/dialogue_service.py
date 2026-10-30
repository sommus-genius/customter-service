from domain.messages import UserMessage, ProcessResult
from domain.state import DialogueState
from engine.dialogue_engine import DialogueEngine
from model import dialogue_state
from repository.dialogue_state_repository import DialogueStateRepository


class DialogueService:
    """
    对话服务
    """
    def __init__(self,
                 dialogue_engine:DialogueEngine,
                 dialogue_state_repository: DialogueStateRepository):
        self.dialogue_engine = dialogue_engine
        self.dialogue_state_repository = dialogue_state_repository


    async def process_message(self,user_message: UserMessage) -> ProcessResult:
        """
        处理用户消息
        :param user_message:
        :return:
        """
        #1.获取用户的对话状态
        dialogue_state = await self.dialogue_state_repository.load_state(user_message.sender_id)

        #2. 根据用户消息，执行对话引擎，获取处理结果
        process_result = await self.dialogue_engine.process_message(dialogue_state,user_message)

        #3.保存对话状态
        await self.dialogue_state_repository.save_state(dialogue_state)

        # 4.返回结果
        return process_result
    