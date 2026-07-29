from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.voice_command import AgentTask, VoiceCommand


class VoiceCommandRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, *, business_id: UUID, user_id: UUID, input_type: str, transcript: str, idempotency_key: str
    ) -> VoiceCommand:
        command = VoiceCommand(
            business_id=business_id,
            user_id=user_id,
            input_type=input_type,
            transcript=transcript,
            status="PENDING",
            idempotency_key=idempotency_key,
        )
        self.session.add(command)
        await self.session.flush()
        return command

    async def get_by_idempotency_key(
        self, *, business_id: UUID, idempotency_key: str
    ) -> VoiceCommand | None:
        result = await self.session.execute(
            select(VoiceCommand).where(
                VoiceCommand.business_id == business_id,
                VoiceCommand.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, *, business_id: UUID, command_id: UUID) -> VoiceCommand | None:
        result = await self.session.execute(
            select(VoiceCommand).where(
                VoiceCommand.id == command_id, VoiceCommand.business_id == business_id
            )
        )
        return result.scalar_one_or_none()

    async def list(self, *, business_id: UUID, status: str | None = None) -> list[VoiceCommand]:
        query = select(VoiceCommand).where(VoiceCommand.business_id == business_id)
        if status is not None:
            query = query.where(VoiceCommand.status == status)
        query = query.order_by(VoiceCommand.created_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())


class AgentTaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        command_id: UUID,
        agent_name: str,
        tool_name: str | None,
        status: str,
        input_json: dict,
        output_json: dict,
    ) -> AgentTask:
        task = AgentTask(
            command_id=command_id,
            agent_name=agent_name,
            tool_name=tool_name,
            status=status,
            input_json=input_json,
            output_json=output_json,
        )
        self.session.add(task)
        await self.session.flush()
        return task
