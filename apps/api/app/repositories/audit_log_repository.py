from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditLogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        business_id: UUID,
        actor_type: str,
        actor_id: str | None,
        action: str,
        entity_type: str,
        entity_id: UUID | None,
        metadata: dict | None,
    ) -> AuditLog:
        """Adds + flushes only — deliberately does NOT commit. Callers write
        audit entries as part of the same transaction as the business
        action they're logging, so a rollback undoes both together.
        """
        log = AuditLog(
            business_id=business_id,
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata or {},
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def list(
        self,
        *,
        business_id: UUID,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 200,
    ) -> list[AuditLog]:
        query = select(AuditLog).where(AuditLog.business_id == business_id)
        if entity_type is not None:
            query = query.where(AuditLog.entity_type == entity_type)
        if entity_id is not None:
            query = query.where(AuditLog.entity_id == entity_id)
        if date_from is not None:
            query = query.where(AuditLog.created_at >= date_from)
        if date_to is not None:
            query = query.where(AuditLog.created_at <= date_to)
        query = query.order_by(AuditLog.created_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
