from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class PaymentStatusBreakdown(BaseModel):
    payment_status: str
    count: int
    amount: Decimal


class DashboardResponse(BaseModel):
    date_from: date
    date_to: date
    total_sales_amount: Decimal
    total_expenses_amount: Decimal
    profit: Decimal
    sale_count: int
    low_stock_count: int
    total_customer_dues: Decimal
    sales_by_payment_status: list[PaymentStatusBreakdown]
