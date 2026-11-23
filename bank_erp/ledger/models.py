from decimal import Decimal

from django.db import models
from django.db.models import Sum


class Customer(models.Model):
    customer_id = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return f"{self.customer_id} - {self.name}"


class Invoice(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        PARTIALLY_PAID = "partially_paid", "Partially paid"
        PAID = "paid", "Paid"

    invoice_number = models.CharField(max_length=32, unique=True)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="invoices",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )

    @property
    def amount_paid(self) -> Decimal:
        total = self.payments.aggregate(total=Sum("amount"))["total"]
        return total or Decimal("0.00")

    @property
    def balance(self) -> Decimal:
        return max(self.amount - self.amount_paid, Decimal("0.00"))

    def __str__(self) -> str:
        return self.invoice_number


class Payment(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name="payments",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=255, unique=True)
    booked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="payment_amount_positive",
            )
        ]

    def __str__(self) -> str:
        return f"{self.invoice.invoice_number} - {self.amount}"
