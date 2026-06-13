from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from budget_app.filters.budget_filter import BudgetSheetFilter
from budget_app.models import BudgetSheet
from budget_app.permissions import BudgetRBACPermission
from budget_app.serializers.budget_serializer import BudgetSheetSerializer
from budget_app.serializers.transfer_serializer import (
    BudgetTransferCreateSerializer,
    BudgetTransferSerializer,
)
from budget_app.services.budget_service import BudgetService
from budget_app.services.transfer_service import BudgetTransferService


class BudgetSheetViewSet(viewsets.ModelViewSet):
    queryset = BudgetSheet.objects.all().order_by("-updated_at")
    serializer_class = BudgetSheetSerializer
    permission_classes = [BudgetRBACPermission]
    filterset_class = BudgetSheetFilter

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        self.approval_action = True
        budget = BudgetService().activate_budget(self.get_object(), str(request.user.id or "system"))
        return Response(self.get_serializer(budget).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def recalculate(self, request, pk=None):
        budget = BudgetService().recalculate(self.get_object(), str(request.user.id or "system"))
        return Response(self.get_serializer(budget).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def transfer(self, request, pk=None):
        self.accounting_action = True
        budget = self.get_object()
        serializer = BudgetTransferCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        if validated["budget_sheet"].id != budget.id:
            return Response(
                {"detail": "调剂项必须属于当前预算表"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        transfer = BudgetTransferService().execute_transfer(
            budget_sheet=budget,
            from_item=validated["from_item"],
            to_item=validated["to_item"],
            transfer_amount=validated["transfer_amount"],
            reason=validated.get("reason", ""),
            actor_id=str(request.user.id or "system"),
        )
        return Response(
            BudgetTransferSerializer(transfer).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def transfers(self, request, pk=None):
        budget = self.get_object()
        qs = budget.transfers.select_related("from_item", "to_item").all()
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = BudgetTransferSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = BudgetTransferSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
