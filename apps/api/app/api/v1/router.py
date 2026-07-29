from fastapi import APIRouter

from app.api.v1.endpoints import (
    analytics,
    audit,
    auth,
    businesses,
    customers,
    documents,
    expenses,
    insights,
    products,
    reminders,
    transactions,
    voice_commands,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(businesses.router)
api_router.include_router(products.router)
api_router.include_router(customers.router)
api_router.include_router(transactions.router)
api_router.include_router(expenses.router)
api_router.include_router(analytics.router)
api_router.include_router(reminders.router)
api_router.include_router(audit.router)
api_router.include_router(voice_commands.router)
api_router.include_router(insights.router)
api_router.include_router(documents.router)
