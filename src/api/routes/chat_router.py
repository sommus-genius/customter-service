import uuid

from fastapi import APIRouter
from fastapi.params import Depends

from api.schemas import ChatRequest, ChatResponse, ChatBotMessage, ChatObject, HistoryResponse, HistoryMessage
from domain.messages import UserMessage, MessageType, FocuseObject, ProcessResult
from service.dialogue_service import DialogueService
from api.routes.dependencies import get_dialogue_service
router = APIRouter()

@router.post("/api/chat")
async def chat_endpoint(
        chat_request: ChatRequest,
        # 依赖注入
        dialogue_service: DialogueService = Depends(get_dialogue_service)
) -> ChatResponse:

    #1.将接口模型转换成领域模型
    user_message = _build_user_message(chat_request)
    #2.业务处理
    process_result = await dialogue_service.process_message(user_message)
    #3.将领域模型转换成接口模型
    return _build_chat_response(process_result)
def _build_user_message(chat_request: ChatRequest) -> UserMessage:
    # 文本消息没有对象数据，默认设为 None
    focused_object = None

    # 只有传入对象数据时，才读取它的字段
    if chat_request.object is not None:
        focused_object = FocuseObject(
            id=chat_request.object.id,
            type=chat_request.object.type,
            title=chat_request.object.title,
            attributes=chat_request.object.attributes,
        )

    return UserMessage(
        sender_id = chat_request.sender_id,
        #如果没有则生成uuid作为message_id,如果有则直接使用chat_request.message_id
        message_id = chat_request.message_id if chat_request.message_id else str(uuid.uuid4()),
        type = MessageType.TEXT if chat_request.text else MessageType.OBJECT,
        text = chat_request.text,
        object = focused_object
    )

def _build_chat_response(process_result: ProcessResult) -> ChatResponse:
    return ChatResponse(
        sender_id = process_result.sender_id,
        message_id  = process_result.message_id,
        messages=[
            ChatBotMessage(
                text = bot_msg.text,
                object = ChatObject(
                    id = bot_msg.object.id,
                    type = bot_msg.object.type,
                    title = bot_msg.object.title,
                    attributes=bot_msg.object.attributes
                ) if not bot_msg.object is None else None
            )
            for bot_msg in process_result.messages
        ]
    )
@router.get('/api/chat/history')
async def history(sender_id: str) -> HistoryResponse:
    # 业务层  ->持久层   ->数据
    return HistoryResponse(
        sender_id = sender_id,
        messages = [
            HistoryMessage(role='user', text='Hello'),
            HistoryMessage(role='bot', text='Hi')
        ]
    )
