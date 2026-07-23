from datetime import date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import DashboardResponse, PaymentStatusBreakdown


class AnalyticsService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AnalyticsRepository(session)

    async def get_dashboard(
        self, *, business_id: UUID, date_from: date | None, date_to: date | None
    ) -> DashboardResponse:
        """Defaults to 'today' (business-server local date) when no range
        is given, matching the dashboard's 'daily operational summary'
        purpose from the frontend design doc. Pass explicit date_from/
        date_to for weekly/monthly views.

        NOTE (documented simplification): 'profit' here is sales minus
        expenses only — it does not yet subtract cost_price (COGS) per
        item sold. True gross-margin profit needs summing
        transaction_items.quantity * product.cost_price, which we can add
        once the Advisor Agent step needs it for pricing suggestions.
        """
        if date_from is None:
            date_from = date.today()
        if date_to is None:
            date_to = date_from

        start = datetime.combine(date_from, time.min)
        end = datetime.combine(date_to, time.max)

        sale_count, total_sales = await self.repo.sum_sales(
            business_id=business_id, start=start, end=end
        )
        total_expenses = await self.repo.sum_expenses(business_id=business_id, start=start, end=end)
        breakdown_rows = await self.repo.sales_by_payment_status(
            business_id=business_id, start=start, end=end
        )
        low_stock_count = await self.repo.low_stock_count(business_id=business_id)
        total_dues = await self.repo.total_customer_dues(business_id=business_id)

        return DashboardResponse(
            date_from=date_from,
            date_to=date_to,
            total_sales_amount=total_sales,
            total_expenses_amount=total_expenses,
            profit=total_sales - total_expenses,
            sale_count=sale_count,
            low_stock_count=low_stock_count,
            total_customer_dues=total_dues,
            sales_by_payment_status=[
                PaymentStatusBreakdown(payment_status=row[0], count=row[1], amount=row[2])
                for row in breakdown_rows
            ],
        )
