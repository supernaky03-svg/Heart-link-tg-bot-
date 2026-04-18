from __future__ import annotations

from app.models.records import PremiumPlan


class PaymentService:
    def build_premium_payload(self, user_id: int, plan: PremiumPlan) -> str:
        return f"premium:{user_id}:{int(plan.plan_id)}:{int(plan.days)}:{int(plan.stars)}"

    def parse_premium_payload(self, payload: str) -> tuple[int, int, int, int] | None:
        try:
            prefix, user_id, plan_id, days, stars = payload.split(":", 4)
            if prefix != "premium":
                return None
            return int(user_id), int(plan_id), int(days), int(stars)
        except Exception:
            return None

    async def apply_successful_premium_payment(self, storage, payment) -> bool:
        parsed = self.parse_premium_payload(payment.invoice_payload)
        if not parsed:
            return False

        user_id, _plan_id, days, _stars = parsed
        profile = storage.get_user_profile(user_id)
        if not profile:
            return False

        await storage.grant_premium(user_id, days, granted_by=user_id)
        await storage.log_admin_action(
            user_id,
            "premium_payment",
            user_id=user_id,
            days=days,
            stars=payment.total_amount,
            currency=payment.currency,
            charge_id=payment.telegram_payment_charge_id,
        )
        return True
