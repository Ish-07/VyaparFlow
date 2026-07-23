from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.audit_log_repository import AuditLogRepository
from app.schemas.audit import AuditLogResponse


class AuditLogService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AuditLogRepository(session)

    async def record(
        self,
        *,
        business_id: UUID,
        actor_type: str,
        actor_id: str | None,
        action: str,
        entity_type: str,
        entity_id: UUID | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Call this BEFORE the caller's own session.commit() — it only
        flushes, so the audit row commits atomically with whatever
        business action it's describing."""
        await self.repo.create(
            business_id=business_id,
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata,
        )

    async def list_logs(
        self,
        *,
        business_id: UUID,
        entity_type: str | None,
        entity_id: UUID | None,
        date_from: date | None,
        date_to: date | None,
    ) -> list[AuditLogResponse]:
        logs = await self.repo.list(
            business_id=business_id,
            entity_type=entity_type,
            entity_id=entity_id,
            date_from=date_from,
            date_to=date_to,
        )
        return [AuditLogResponse.model_validate(log) for log in logs]
