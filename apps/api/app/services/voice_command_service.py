from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph import build_agent_graph
from app.core.config import get_settings
from app.repositories.product_repository import ProductRepository
from app.repositories.voice_command_repository import AgentTaskRepository, VoiceCommandRepository
from app.schemas.voice_command import (
    VoiceCommandConfirmRequest,
    VoiceCommandCreateRequest,
    VoiceCommandResponse,
)
from app.services.ai.base import ParsedCommand
from app.services.ai.router import AIRouter

settings = get_settings()


class VoiceCommandService:
    """Orchestrates the command lifecycle:
    PENDING -> UNDERSTANDING -> EXECUTING -> COMPLETED
                              -> NEEDS_CONFIRMATION -> (via confirm()) -> COMPLETED / FAILED

    "Understanding" (intent/entity extraction) is delegated to AIRouter,
    which tries a real LLM (NVIDIA NIM) first and falls back to the
    Step 6 rule-based parser if unavailable.

    "Orchestration and execution" (Step 8) is delegated to a real
    LangGraph StateGraph (app/agent/graph.py) - a Supervisor node routes
    to specialized agents (Inventory, Finance, Clarification), and a
    successful SALE conditionally chains into an Advisor agent for a
    restock suggestion. This class no longer contains any if/elif
    dispatch logic itself; it only builds the initial graph state,
    invokes the graph, and translates the resulting state back onto the
    VoiceCommand row + agent_tasks log.

    Safety note, unchanged from Step 7: nothing here trusts an LLM's own
    confidence/completeness claims. The supervisor node independently
    re-validates required entities, and every agent's actual execution
    goes through the same FastAPI services (tenant scope, stock policy,
    confirmation rules) that the plain REST endpoints use - see
    app/agent/tools.py's docstring.
    """

    def __init__(self, session: AsyncSession, ai_router: AIRouter | None = None):
        self.session = session
        self.commands = VoiceCommandRepository(session)
        self.tasks = AgentTaskRepository(session)
        self.products = ProductRepository(session)
        self.ai_router = ai_router or AIRouter()

    async def _log_task(self, *, command_id, agent_name, tool_name, status_, input_json, output_json):
        await self.tasks.create(
            command_id=command_id,
            agent_name=agent_name,
            tool_name=tool_name,
            status=status_,
            input_json=input_json,
            output_json=output_json,
        )

    async def _log_tool_results(self, *, command_id, tool_results: list[dict]) -> None:
        for result in tool_results:
            await self._log_task(
                command_id=command_id,
                agent_name=result.get("agent", "unknown_agent"),
                tool_name=result.get("tool"),
                status_=result.get("status", "UNKNOWN"),
                input_json={k: v for k, v in result.items() if k not in ("agent", "tool", "status")},
                output_json=result,
            )

    async def _run_graph_and_apply(self, *, command, initial_state: dict) -> None:
        graph = build_agent_graph(self.session)
        final_state = await graph.ainvoke(initial_state)

        await self._log_tool_results(
            command_id=command.id, tool_results=final_state.get("tool_results", [])
        )

        command.status = final_state.get("status", "FAILED")
        command.final_response = final_state.get("final_response")
        if command.status == "COMPLETED":
            command.completed_at = datetime.utcnow()

    async def create_command(
        self, *, business_id: UUID, user_id: UUID, payload: VoiceCommandCreateRequest
    ) -> VoiceCommandResponse:
        existing = await self.commands.get_by_idempotency_key(
            business_id=business_id, idempotency_key=payload.idempotency_key
        )
        if existing:
            return VoiceCommandResponse.model_validate(existing)

        command = await self.commands.create(
            business_id=business_id,
            user_id=user_id,
            input_type=payload.input_type,
            transcript=payload.text,
            idempotency_key=payload.idempotency_key,
        )

        known_products = await self.products.list(business_id=business_id, is_active=True)
        business_context = {"known_products": [p.name for p in known_products]}

        parsed: ParsedCommand = await self.ai_router.parse_command(payload.text, business_context)
        command.intent = parsed.intent
        command.entities = parsed.entities
        command.confidence = parsed.confidence
        command.status = "UNDERSTANDING"

        await self._log_task(
            command_id=command.id,
            agent_name=parsed.provider_used,
            tool_name="parse_command",
            status_="SUCCESS",
            input_json={"text": payload.text},
            output_json={
                "intent": parsed.intent,
                "entities": parsed.entities,
                "confidence": parsed.confidence,
                "model_used": parsed.model_used,
                "latency_ms": round(parsed.latency_ms, 1),
                "fallback_reason": parsed.fallback_reason,
            },
        )

        command.status = "EXECUTING"
        initial_state = {
            "command_id": command.id,
            "business_id": business_id,
            "user_id": user_id,
            "transcript": payload.text,
            "intent": parsed.intent,
            "confidence": parsed.confidence,
            "entities_raw": parsed.entities,
            "_confidence_threshold": settings.command_confidence_threshold,
            "payment_status": "PAID",
            "confirm_negative_stock": False,
            "tool_results": [],
        }
        await self._run_graph_and_apply(command=command, initial_state=initial_state)

        await self.session.commit()
        await self.session.refresh(command)
        return VoiceCommandResponse.model_validate(command)

    async def confirm_command(
        self, *, business_id: UUID, user_id: UUID, command_id: UUID, payload: VoiceCommandConfirmRequest
    ) -> VoiceCommandResponse:
        command = await self.commands.get_by_id(business_id=business_id, command_id=command_id)
        if not command:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Command not found")
        if command.status != "NEEDS_CONFIRMATION":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Command is in status {command.status}, not awaiting confirmation.",
            )
        if command.intent not in ("SALE", "EXPENSE", "STOCK_UPDATE"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Confirmation not supported for intent {command.intent}",
            )
        if command.intent in ("SALE", "STOCK_UPDATE") and not payload.product_id and not command.entities.get(
            "product_name"
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="product_id is required to confirm this command",
            )

        initial_state = {
            "command_id": command.id,
            "business_id": business_id,
            "user_id": user_id,
            "transcript": command.transcript,
            "intent": command.intent,
            "confidence": 1.0,
            "entities_raw": command.entities or {},
            "_confidence_threshold": settings.command_confidence_threshold,
            "product_id": str(payload.product_id) if payload.product_id else None,
            "quantity": payload.quantity,
            "unit_price": payload.unit_price,
            "amount": payload.amount,
            "category": payload.category,
            "payment_status": payload.payment_status,
            "customer_id": str(payload.customer_id) if payload.customer_id else None,
            "confirm_negative_stock": payload.confirm_negative_stock,
            "tool_results": [],
        }
        await self._run_graph_and_apply(command=command, initial_state=initial_state)

        await self.session.commit()
        await self.session.refresh(command)
        return VoiceCommandResponse.model_validate(command)

    async def get_command(self, *, business_id: UUID, command_id: UUID) -> VoiceCommandResponse:
        command = await self.commands.get_by_id(business_id=business_id, command_id=command_id)
        if not command:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Command not found")
        return VoiceCommandResponse.model_validate(command)

    async def list_commands(
        self, *, business_id: UUID, status_filter: str | None
    ) -> list[VoiceCommandResponse]:
        commands = await self.commands.list(business_id=business_id, status=status_filter)
        return [VoiceCommandResponse.model_validate(c) for c in commands]
