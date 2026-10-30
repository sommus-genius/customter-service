import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import Session

from domain.state import DialogueState
from model import dialogue_state


class DialogueStateRepository:

    def __init__(self,session: AsyncSession):
        self.session = session

    async def load_state(self,sender_id: str) -> DialogueState:
        # 组装sql语句对象
        select_statement = select(
            dialogue_state.DialogueStateRecord
        ).where(
            dialogue_state.DialogueStateRecord.sender_id == sender_id
        )
        # 执行sql语句对象，获取结果
        result = await self.session.execute(select_statement)
        # 从结果中获取state对象
        state = result.scalars().one_or_none()

        if state :
            # 从数据库中获取state_json,并转换为字典
            state_dict = json.loads(state.state_json)

            return DialogueState.model_validate(state_dict)

        return DialogueState(sender_id=sender_id)


    async def save_state(self, dialoguestate: DialogueState):
        """
        插入：insert
        更新：update
        :param dialoguestate:
        :return:
        """
        # 对象转成字典
        state_json = json.dumps(dialoguestate.model_dump(mode="json"))
        # 定义插入的sql语句
        insert_statement = insert(dialogue_state.DialogueStateRecord).values(
            sender_id = dialoguestate.sender_id,
            state_json = state_json
        )
        #一旦主键升级就升级为update
        update_statement = insert_statement.on_duplicate_key_update(
            state_json=insert_statement.inserted.state_json
        )
        # 执行sql语句对象
        await self.session.execute(update_statement)
        # 提交事务
        await self.session.commit()
