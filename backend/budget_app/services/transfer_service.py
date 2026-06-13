from decimal import Decimal

from django.db import transaction

from budget_app.models import AuditLog, BudgetItem, BudgetSheet, BudgetTransfer


class BudgetTransferError(Exception):
    pass


class BudgetTransferService:
    @staticmethod
    def _locked_items(from_item_id: int, to_item_id: int):
        first_id, second_id = sorted((from_item_id, to_item_id))
        locked = {
            item.id: item
            for item in BudgetItem.objects.filter(id__in=[first_id, second_id]).select_for_update()
        }
        if from_item_id not in locked or to_item_id not in locked:
            raise BudgetTransferError("预算项不存在或已被删除")
        return locked[from_item_id], locked[to_item_id]

    @staticmethod
    def _locked_sheet(sheet_id: int) -> BudgetSheet:
        try:
            return BudgetSheet.objects.select_for_update().get(id=sheet_id)
        except BudgetSheet.DoesNotExist:
            raise BudgetTransferError("预算表不存在或已被删除")

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
        if transfer_amount <= 0:
            raise BudgetTransferError("调剂金额必须大于 0")
        if from_item.id == to_item.id:
            raise BudgetTransferError("转出项和转入项不能相同")

        locked_from, locked_to = self._locked_items(from_item.id, to_item.id)
        locked_sheet = self._locked_sheet(budget_sheet.id)

        if locked_from.budget_sheet_id != locked_sheet.id or locked_to.budget_sheet_id != locked_sheet.id:
            raise BudgetTransferError("调剂项必须属于当前预算表")

        if locked_sheet.status != "Active":
            raise BudgetTransferError("仅可在已启用（Active）的预算表内进行调剂")

        available = locked_from.budget_amount - locked_from.spent_amount
        if available < transfer_amount:
            raise BudgetTransferError(
                f"转出项可用余额不足，当前可用 {available}，调剂金额 {transfer_amount}"
            )

        from_before = {
            "budget_amount": str(locked_from.budget_amount),
            "variance_amount": str(locked_from.variance_amount),
        }
        to_before = {
            "budget_amount": str(locked_to.budget_amount),
            "variance_amount": str(locked_to.variance_amount),
        }

        locked_from.budget_amount -= transfer_amount
        locked_from.recalculate_variance()
        locked_from.save(update_fields=["budget_amount", "variance_amount", "updated_at"])

        locked_to.budget_amount += transfer_amount
        locked_to.recalculate_variance()
        locked_to.save(update_fields=["budget_amount", "variance_amount", "updated_at"])

        locked_sheet.version += 1
        locked_sheet.save(update_fields=["version", "updated_at"])

        transfer = BudgetTransfer.objects.create(
            budget_sheet=locked_sheet,
            from_item=locked_from,
            to_item=locked_to,
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
                    "budget_amount": str(locked_from.budget_amount),
                    "variance_amount": str(locked_from.variance_amount),
                },
                "to_item": {
                    "budget_amount": str(locked_to.budget_amount),
                    "variance_amount": str(locked_to.variance_amount),
                },
                "transfer_amount": str(transfer_amount),
            },
        )

        return transfer
