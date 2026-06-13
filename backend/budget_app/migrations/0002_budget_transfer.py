import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("budget_app", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="BudgetTransfer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("transfer_amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("reason", models.TextField(blank=True, default="")),
                ("operator_id", models.CharField(blank=True, default="", max_length=64)),
                (
                    "budget_sheet",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="transfers", to="budget_app.budgetsheet"),
                ),
                (
                    "from_item",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="outgoing_transfers", to="budget_app.budgetitem"),
                ),
                (
                    "to_item",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="incoming_transfers", to="budget_app.budgetitem"),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
