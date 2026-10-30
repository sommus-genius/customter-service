from pathlib import Path

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from chitchat.handler import ChitChatHandler
from chitchat.responder import ChitChatResponder
from clarify.responder import ClarifyResponder
from engine.dialogue_engine import DialogueEngine
from infrastructure import database
from knowledge.handler import KnowledgeHandler
from knowledge.intents import KNOWLEDGE_INTENTS
from knowledge.providers import ProductAPIProvider, OrderAPIProvider, FAQProvider, RAGProvider
from knowledge.registry import KnowledgeProviderRegistry
from knowledge.responder import KnowledgeResponder
from repository.dialogue_state_repository import DialogueStateRepository
from service.dialogue_service import DialogueService
from plan.turn_planner import TurnPlanner
from task.action.builder import build_action_runner
from task.command.processor import CommandProcessor
from task.flow.executor import FlowExecutor
from task.flow.loader import FlowLoader
from task.handler import TaskHandler
from task.flow.flows import FlowsList
from plan.turn_validator import TurnPlanValidator
async def get_session():
    """
    执行流程：
    1.进入 async with async_session() as session: 打开session
    2.yield: 将session交给他的调用者
    3.路由函数执行完毕：回到yield 之后，关闭session
    """
    async with database.async_session() as session:
        yield session

async def get_dialogue_state_repository(session: AsyncSession = Depends(get_session)):
    return DialogueStateRepository(session=session)

async def get_dialogue_engine():
    base_path = Path(__file__).parents[3]
    user_flow_path = base_path / "flow_config" / "user_flows.yml"
    system_flow_path = base_path / "flow_config" / "system_flows.yml"
    loader = FlowLoader()
    flow_list = loader.load_many([user_flow_path, system_flow_path])
    provider_registry = KnowledgeProviderRegistry([
        ProductAPIProvider(), OrderAPIProvider(), FAQProvider(), RAGProvider(),
    ])

    return DialogueEngine(
        turn_planner=TurnPlanner(),
        task_handler=TaskHandler(
            flows=flow_list,
            command_processor=CommandProcessor(),
            action_runner=build_action_runner(),
            flow_executor=FlowExecutor(),
        ),
        knowledge_handler=KnowledgeHandler(
            knowledge_intents=KNOWLEDGE_INTENTS,
            provider_registry=provider_registry,
            knowledge_responder=KnowledgeResponder(),
        ),
        provider_registry=provider_registry,
        turn_planner_validator=TurnPlanValidator(),
        clarify_responder=ClarifyResponder(),
        chitchat_handler=ChitChatHandler(responder= ChitChatResponder()),
    )

async def get_dialogue_service(
        dialogue_engine : DialogueEngine = Depends(get_dialogue_engine),
        dialogue_state_repository: DialogueStateRepository = Depends(get_dialogue_state_repository)):
    return DialogueService(
        dialogue_engine = dialogue_engine,
        dialogue_state_repository = dialogue_state_repository
    )

