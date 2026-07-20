from fastapi import APIRouter

from app.api.v1.endpoints import auth, businesses, customers, expenses, products, transactions

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(businesses.router)
api_router.include_router(products.router)
api_router.include_router(customers.router)
api_router.include_router(transactions.router)
api_router.include_router(expenses.router)
