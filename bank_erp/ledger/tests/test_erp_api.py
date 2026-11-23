from decimal import Decimal
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from ledger.models import Customer, Invoice, Payment


@pytest.fixture
def api_client(db):
    user = get_user_model().objects.create_user(username="api-test")
    token = Token.objects.create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.fixture
def invoice(db):
    customer = Customer.objects.create(customer_id="CUST-001", name="Müller Maschinenbau GmbH")
    return Invoice.objects.create(
        invoice_number="INV-2025-0001",
        customer=customer,
        amount=Decimal("1000.00"),
        due_date="2025-01-31",
    )


@pytest.mark.django_db
def test_seed_erp_creates_customers_and_invoices():
    with NamedTemporaryFile("w", newline="", encoding="utf-8", suffix=".csv", delete=False) as handle:
        handle.write(
            "invoice_number,customer_id,customer_name,amount_eur,due_date\n"
            "INV-2025-0001,CUST-001,Müller GmbH,1234.50,2025-01-31\n"
            "INV-2025-0002,CUST-001,Müller GmbH,250.00,2025-02-28\n"
        )
        csv_path = handle.name

    call_command("seed_erp", csv=csv_path)
    call_command("seed_erp", csv=csv_path)

    assert Customer.objects.count() == 1
    assert Invoice.objects.count() == 2
    assert Invoice.objects.get(invoice_number="INV-2025-0001").amount == Decimal("1234.50")


@pytest.mark.django_db
def test_listing_open_invoices(api_client, invoice):
    response = api_client.get("/api/invoices/?status=unpaid")
    assert response.status_code == 200
    assert response.data[0]["invoice_number"] == "INV-2025-0001"
    assert Decimal(response.data[0]["balance"]) == Decimal("1000.00")
    assert response.data[0]["customer_name"] == "Müller Maschinenbau GmbH"


@pytest.mark.django_db
def test_valid_payment(api_client, invoice):
    response = api_client.post(
        "/api/payments/",
        {
            "invoice_number": invoice.invoice_number,
            "amount": "1000.00",
            "reference": "Rechnung INV-2025-0001",
            "idempotency_key": "pay-1",
        },
        format="json",
    )
    assert response.status_code == 201
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.PAID
    assert Payment.objects.count() == 1


@pytest.mark.django_db
def test_partial_payment_changes_status(api_client, invoice):
    response = api_client.post(
        "/api/payments/",
        {
            "invoice_number": invoice.invoice_number,
            "amount": "400.00",
            "idempotency_key": "pay-partial",
        },
        format="json",
    )
    assert response.status_code == 201
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.PARTIALLY_PAID
    assert invoice.amount_paid == Decimal("400.00")
    assert invoice.balance == Decimal("600.00")


@pytest.mark.django_db
def test_overpayment_rejected(api_client, invoice):
    response = api_client.post(
        "/api/payments/",
        {
            "invoice_number": invoice.invoice_number,
            "amount": "1000.01",
            "idempotency_key": "pay-over",
        },
        format="json",
    )
    assert response.status_code == 400
    assert Payment.objects.count() == 0


@pytest.mark.django_db
def test_duplicate_idempotency_key_returns_same_payment(api_client, invoice):
    payload = {
        "invoice_number": invoice.invoice_number,
        "amount": "250.00",
        "reference": "Teilzahlung",
        "idempotency_key": "pay-duplicate",
    }
    first = api_client.post("/api/payments/", payload, format="json")
    second = api_client.post("/api/payments/", payload, format="json")

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.data["id"] == second.data["id"]
    assert Payment.objects.count() == 1


@pytest.mark.django_db
def test_unauthenticated_requests_rejected():
    client = APIClient()
    assert client.get("/api/invoices/").status_code in (401, 403)
    assert client.post(
        "/api/payments/",
        {"invoice_number": "INV-2025-0001", "amount": "1.00", "idempotency_key": "no-auth"},
        format="json",
    ).status_code in (401, 403)
