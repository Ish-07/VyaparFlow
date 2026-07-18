"""
Import every model module here so that Base.metadata is fully populated
for Alembic's autogenerate and for app startup.
"""

from app.models.audit_log import AuditLog  # noqa: F401
from app.models.business import Business, BusinessMember, User  # noqa: F401
from app.models.customer import Customer  # noqa: F401
from app.models.document import Document, DocumentChunk, RetrievalLog  # noqa: F401
from app.models.insight import Insight, Reminder  # noqa: F401
from app.models.product import Product, StockMovement  # noqa: F401
from app.models.transaction import Expense, Transaction, TransactionItem  # noqa: F401
from app.models.voice_command import AgentTask, VoiceCommand  # noqa: F401
