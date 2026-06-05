"""A2A narrator agent: wraps the Granite offside explanation as an A2A skill.

Serves the Agent Card at ``/.well-known/agent-card.json`` and handles
``message/send`` (JSON-RPC), using the official a2a-sdk (the same pattern as the
``a2aproject/a2a-samples`` helloworld). Registered with the Context Forge gateway
(``POST /a2a`` ``{name, endpoint_url}``) -> exposed as the tool ``a2a_narrator``.
Run standalone (JSON-RPC on :9000):

    python -m app.a2a_agent.narrator
"""

from __future__ import annotations

import asyncio
import json
import logging

import uvicorn
from a2a.helpers import (
    get_message_text,
    new_task_from_user_message,
    new_text_message,
    new_text_part,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from a2a.types.a2a_pb2 import TaskState
from starlette.applications import Starlette

from app.llm.granite import GraniteClient

NARRATOR_PORT = 9000

_log = logging.getLogger("varsity")

_CANNED_LAW = (
    "A player is offside if any part of the head, body or feet is nearer the "
    "opponents' goal line than both the ball and the second-last opponent when "
    "the ball is played (Law 11)."
)


def narrate(payload: str, *, granite: object | None = None) -> str:
    """Produce a Law-grounded offside explanation from a JSON decision payload.

    ``payload`` is a JSON string ``{margin_meters, is_offside, law_text, language?}``.
    Falls back to the canned WC2022 offside if it is not valid decision JSON, so the
    agent always returns a usable explanation.
    """
    granite = granite or GraniteClient()
    try:
        data = json.loads(payload)
        return granite.explain_offside(
            margin_meters=float(data["margin_meters"]),
            is_offside=bool(data["is_offside"]),
            law_text=str(data.get("law_text") or _CANNED_LAW),
            language=str(data.get("language", "English")),
        )
    except (ValueError, KeyError, TypeError):
        _log.warning("narrator payload not valid decision JSON; using the canned demo offside")
        return granite.explain_offside(
            margin_meters=5.69, is_offside=True, law_text=_CANNED_LAW
        )


class NarratorExecutor(AgentExecutor):
    """Runs the (blocking) Granite explanation off the event loop and returns it."""

    def __init__(self, granite: object | None = None) -> None:
        self._granite = granite

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task or new_task_from_user_message(context.message)
        if not context.current_task:
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(
            event_queue=event_queue, task_id=task.id, context_id=task.context_id
        )
        await updater.update_status(
            state=TaskState.TASK_STATE_WORKING, message=new_text_message("Narrating...")
        )
        query = get_message_text(context.message) or ""
        result = await asyncio.to_thread(narrate, query, granite=self._granite)
        await updater.add_artifact(parts=[new_text_part(text=result, media_type="text/plain")])
        await updater.update_status(
            state=TaskState.TASK_STATE_COMPLETED, message=new_text_message("Done.")
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Cancel is not supported.")


def agent_card(host: str = "127.0.0.1", port: int = NARRATOR_PORT) -> AgentCard:
    skill = AgentSkill(
        id="narrate_offside",
        name="Narrate offside decision",
        description=(
            "Explain a VAR offside decision in plain, Law-grounded language for a blind fan."
        ),
        input_modes=["text/plain"],
        output_modes=["text/plain"],
        tags=["soccer", "var", "offside", "accessibility", "ifab"],
        examples=['{"margin_meters": 5.69, "is_offside": true, "law_text": "...Law 11..."}'],
    )
    return AgentCard(
        name="VARSITY Narrator",
        description=(
            "Turns a structured VAR offside decision into a rule-grounded spoken explanation."
        ),
        version="0.1.0",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=True),
        supported_interfaces=[
            AgentInterface(protocol_binding="JSONRPC", url=f"http://{host}:{port}")
        ],
        skills=[skill],
    )


def build_app(
    host: str = "127.0.0.1", port: int = NARRATOR_PORT, granite: object | None = None
) -> Starlette:
    card = agent_card(host, port)
    handler = DefaultRequestHandler(
        agent_executor=NarratorExecutor(granite=granite),
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )
    routes: list = []
    routes.extend(create_agent_card_routes(card))
    routes.extend(create_jsonrpc_routes(handler, "/"))
    return Starlette(routes=routes)


if __name__ == "__main__":
    uvicorn.run(build_app(host="0.0.0.0"), host="0.0.0.0", port=NARRATOR_PORT)
