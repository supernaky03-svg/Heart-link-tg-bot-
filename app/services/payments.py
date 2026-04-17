from __future__ import annotations

from dataclasses import dataclass

from app.models.records import PremiumPlan


@dataclass
class PaymentQuote:
    title: str
    description: str
    amount_stars: int
    payload: str


class PaymentService:
    """
    Placeholder payment layer.
    Telegram Stars / invoices can be added here later without changing handlers.
    """

    def build_premium_quote(self, plan: PremiumPlan) -> PaymentQuote:
        return PaymentQuote(
            title=f"Heart Link Premium {plan.days} days",
            description=f"Premium boost for {plan.days} days",
            amount_stars=plan.stars,
            payload=f"premium:{plan.plan_id}:{plan.days}:{plan.stars}",
        )
