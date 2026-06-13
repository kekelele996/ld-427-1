from decimal import Decimal

from rest_framework import serializers

from budget_app.models import BudgetItem, BudgetSheet, BudgetStatus, BudgetTransfer


class BudgetTransferCreateSerializer(serializers.Serializer):
    from_item_id = serializers.IntegerField()
    to_item_id = serializers.IntegerField()
    transfer_amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    reason = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        from_item_id = attrs["from_item_id"]
        to_item_id = attrs["to_item_id"]

        if from_item_id == to_item_id:
            raise serializers.ValidationError("转出项和转入项不能相同")

        try:
            from_item = BudgetItem.objects.select_related("budget_sheet").get(id=from_item_id)
        except BudgetItem.DoesNotExist:
            raise serializers.ValidationError({"from_item_id": "转出预算项不存在"})

        try:
            to_item = BudgetItem.objects.select_related("budget_sheet").get(id=to_item_id)
        except BudgetItem.DoesNotExist:
            raise serializers.ValidationError({"to_item_id": "转入预算项不存在"})

        if from_item.budget_sheet_id != to_item.budget_sheet_id:
            raise serializers.ValidationError("转出项和转入项必须属于同一张预算表")

        budget_sheet: BudgetSheet = from_item.budget_sheet
        if budget_sheet.status != BudgetStatus.ACTIVE:
            raise serializers.ValidationError("仅可在已启用（Active）的预算表内进行调剂")

        available = from_item.budget_amount - from_item.spent_amount
        if available < attrs["transfer_amount"]:
            raise serializers.ValidationError(
                {"transfer_amount": f"转出项可用余额不足，当前可用 {available}"}
            )

        attrs["from_item"] = from_item
        attrs["to_item"] = to_item
        attrs["budget_sheet"] = budget_sheet
        return attrs


class BudgetTransferSerializer(serializers.ModelSerializer):
    from_item_name = serializers.CharField(source="from_item.subcategory_name", read_only=True)
    to_item_name = serializers.CharField(source="to_item.subcategory_name", read_only=True)

    class Meta:
        model = BudgetTransfer
        fields = [
            "id",
            "budget_sheet",
            "from_item",
            "from_item_name",
            "to_item",
            "to_item_name",
            "transfer_amount",
            "reason",
            "operator_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["operator_id", "created_at", "updated_at"]
