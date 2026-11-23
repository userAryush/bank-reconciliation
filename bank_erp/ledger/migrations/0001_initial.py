# Generated for the bank ERP ledger app.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Customer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("customer_id", models.CharField(max_length=32, unique=True)),
                ("name", models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name="Invoice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("invoice_number", models.CharField(max_length=32, unique=True)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("due_date", models.DateField()),
                ("status", models.CharField(choices=[("open", "Open"), ("partially_paid", "Partially paid"), ("paid", "Paid")], default="open", max_length=20)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="invoices", to="ledger.customer")),
            ],
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("reference", models.TextField(blank=True)),
                ("idempotency_key", models.CharField(max_length=255, unique=True)),
                ("booked_at", models.DateTimeField(auto_now_add=True)),
                ("invoice", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payments", to="ledger.invoice")),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(condition=models.Q(("amount__gt", 0)), name="payment_amount_positive"),
                ],
            },
        ),
    ]
