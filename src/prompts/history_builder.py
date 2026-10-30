
from domain.messages import MessageType, FocuseObject, BotMessage, UserMessage
from domain.state import Turn


class HistoryBuilder:
    """
    历史记录构建器
    """

    @staticmethod
    def build(truns: list[Turn]) -> str:
        """
        构建历史对话列表的字符串形式
        :param truns:
        :return:
        """

        msgs: list[str] = []
        for turn in truns:
            #1. 用户消息字符串组装
            user_message = turn.user_message
            user_message_str = HistoryBuilder._render_user_message(user_message)
            msgs.append(f"USER:{user_message_str}")

            #2. 机器人消息字符串组装
            bot_messages = turn.bot_message
            for bot_message in bot_messages:
                bot_message_str = HistoryBuilder._render_bot_message(bot_message)
                msgs.append(f"BOT:{bot_message_str}")

        return "\n".join(msgs)


    @staticmethod
    def _render_user_message( user_message):
        """
        用户消息字符串组装
        :param user_message:
        :return:
        """
        if user_message.type == MessageType.TEXT:
            return HistoryBuilder._render_text_msg(user_message.text)
        else:
            return HistoryBuilder._render_obj_msg(user_message.object)

    @staticmethod
    def render_user_message(user_message):
        return HistoryBuilder._render_user_message(user_message)

    @staticmethod
    def _render_bot_message(bot_message: BotMessage) -> str:
        if bot_message.text is not None:
            return HistoryBuilder._render_text_msg(bot_message.text)
        else:
            return HistoryBuilder._render_obj_msg(bot_message.object)

    @staticmethod
    def _render_text_msg(text) -> str:
        return text.strip()

    @staticmethod
    def _render_obj_msg(object_msg: FocuseObject) -> str:
        label = "订单对象" if object_msg.type == "order" else "商品对象"
        id = object_msg.id
        title = object_msg.title
        attributes = object_msg.attributes
        attribute_str = ",".join([f"{k}={v}" for k, v in attributes.items()])
        return f"[label={label},id={id},title={title}, attributed={attribute_str}]"



if __name__ == "__main__":
    # 第一轮：用户发送文本，机器人回复文本
    text_turn = Turn(
        turn_id="turn001",
        user_message=UserMessage(
            sender_id="user001",
            message_id="msg001",
            type=MessageType.TEXT,
            text="你好，我想申请退款",
        ),
        bot_message=[
            BotMessage(text="好的，请选择需要退款的订单。"),
        ],
    )

    # 第二轮：用户发送订单对象，机器人回复文本和订单对象
    order = FocuseObject(
        id="order001",
        type="order",
        title="无线蓝牙耳机",
        attributes={
            "price": "199.00",
            "quantity": "1",
            "status": "已签收",
        },
    )

    object_turn = Turn(
        turn_id="turn002",
        user_message=UserMessage(
            sender_id="user001",
            message_id="msg002",
            type=MessageType.OBJECT,
            object=order,
        ),
        bot_message=[
            BotMessage(text="已找到你的订单，请说明退款原因。"),
            BotMessage(object=order),
        ],
    )

    result = HistoryBuilder.build([text_turn, object_turn])
    print(result)