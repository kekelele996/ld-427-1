from rest_framework import viewsets

from budget_app.models import BudgetTransfer
from budget_app.permissions import BudgetRBACPermission
from budget_app.serializers.transfer_serializer import BudgetTransferSerializer


class BudgetTransferViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BudgetTransfer.objects.select_related("budget_sheet", "from_item", "to_item").all()
    serializer_class = BudgetTransferSerializer
    permission_classes = [BudgetRBACPermission]
    filterset_fields = ["budget_sheet", "from_item", "to_item"]
