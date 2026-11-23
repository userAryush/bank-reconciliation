from django.contrib import admin
from .models import Customer, Invoice, Payment


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("customer_id", "name")
    search_fields = ("customer_id", "name")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "customer", "amount", "status", "due_date")
    list_filter = ("status",)
    search_fields = ("invoice_number", "customer__customer_id", "customer__name")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("invoice", "amount", "idempotency_key", "booked_at")
    search_fields = ("invoice__invoice_number", "reference", "idempotency_key")
