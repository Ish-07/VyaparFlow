from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: UUID
    actor_type: str
    actor_id: str | None
    action: str
    entity_type: str
    entity_id: UUID | None
    metadata_json: dict
    created_at: datetime

    class Config:
        from_attributes = True
