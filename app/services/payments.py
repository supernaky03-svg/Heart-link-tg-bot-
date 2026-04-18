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
    def build_premium_quote(self, user_id: int, plan: PremiumPlan) -> PaymentQuote:
        return PaymentQuote(
            title=f"Heart Link Premium • {plan.days} days",
            description=(
                "Activate Premium and be at the top ✨\n\n"
                "Stand out from others:\n"
                "📈 More profile views\n"
                "🚀 More likes\n"
                "👀 Your likes are seen first\n"
                "⭐️ Your profile ranks higher\n\n"
                "More attention. More matches. More connections 💫"
            ),
            amount_stars=plan.stars,
            payload=f"premium:{user_id}:{plan.plan_id}:{plan.days}:{plan.stars}",
        )

    def parse_premium_payload(self, payload: str) -> tuple[int, int, int, int] | None:
        try:
            prefix, user_id, plan_id, days, stars = payload.split(":", 4)
            if prefix != "premium":
                return None
            return int(user_id), int(plan_id), int(days), int(stars)
        except Exception:
            return None
