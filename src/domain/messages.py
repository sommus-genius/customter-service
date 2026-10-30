from pydantic import BaseModel
from enum import Enum
"""
    定义消息的结构.提供了基本的序列化功能
"""

class FocuseObject(BaseModel):
    id:str #对象的唯一标识
    type:str #对象类型
    title:str | None = None #对象标题（订单标题或者商品名称）
    attributes:dict = {} #其他额外信息

class MessageType(Enum):
    TEXT = "text"
    OBJECT = "object"

# 用户消息
class UserMessage(BaseModel):
    sender_id:str
    message_id:str
    type:MessageType
    text:str | None = None
    object:FocuseObject | None = None

class BotMessage(BaseModel) : 
    text:str | None = None
    object:FocuseObject | None = None


class ProcessResult(BaseModel):
    """
    组装好的最终的业务信息
    """
    sender_id: str # 用户ID
    message_id: str # 消息ID
    messages: list[BotMessage] # 回复消息（机器人消息列表）

    

if __name__ == '__main__':
    message = FocuseObject(id="123", type="order", title="订单标题", description="订单描述", attributes={"key":"value"})

    data = message.model_dump(mode="json")
    data_fo = FocuseObject.model_validate(data)
    print(data)
    print(data_fo)
