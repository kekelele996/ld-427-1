from decimal import Decimal

from django.db import transaction

from budget_app.models import AuditLog, BudgetItem, BudgetSheet, BudgetTransfer


class BudgetTransferService:
    @transaction.atomic
    def execute_transfer(
        self,
        budget_sheet: BudgetSheet,
        from_item: BudgetItem,
        to_item: BudgetItem,
        transfer_amount: Decimal,
        reason: str,
        actor_id: str,
    ) -> BudgetTransfer:
        from_before = {
            "budget_amount": str(from_item.budget_amount),
            "variance_amount": str(from_item.variance_amount),
        }
        to_before = {
            "budget_amount": str(to_item.budget_amount),
            "variance_amount": str(to_item.variance_amount),
        }

        from_item.budget_amount -= transfer_amount
        from_item.recalculate_variance()
        from_item.save(update_fields=["budget_amount", "variance_amount", "updated_at"])

        to_item.budget_amount += transfer_amount
        to_item.recalculate_variance()
        to_item.save(update_fields=["budget_amount", "variance_amount", "updated_at"])

        budget_sheet.version += 1
        budget_sheet.save(update_fields=["version", "updated_at"])

        transfer = BudgetTransfer.objects.create(
            budget_sheet=budget_sheet,
            from_item=from_item,
            to_item=to_item,
            transfer_amount=transfer_amount,
            reason=reason,
            operator_id=actor_id,
        )

        AuditLog.objects.create(
            actor_id=actor_id,
            action="budget.transfer",
            entity_type="BudgetTransfer",
            entity_id=str(transfer.id),
            before={
                "from_item": from_before,
                "to_item": to_before,
            },
            after={
                "from_item": {
                    "budget_amount": str(from_item.budget_amount),
                    "variance_amount": str(from_item.variance_amount),
                },
                "to_item": {
                    "budget_amount": str(to_item.budget_amount),
                    "variance_amount": str(to_item.variance_amount),
                },
                "transfer_amount": str(transfer_amount),
            },
        )

        return transfer
