import csv
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand

from ledger.models import Customer, Invoice


class Command(BaseCommand):
    help = "Seed customers and invoices from the generated open-invoices CSV."

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            dest="csv_path",
            default="../data/output/open_invoices.csv",
            help="Path to open_invoices.csv",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        if not csv_path.is_absolute():
            csv_path = (Path.cwd() / csv_path).resolve()

        customers_created: set[str] = set()
        customers_updated: set[str] = set()
        invoices_created: set[str] = set()
        invoices_updated: set[str] = set()

        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                customer, customer_was_created = Customer.objects.update_or_create(
                    customer_id=row["customer_id"],
                    defaults={"name": row["customer_name"]},
                )
                if customer_was_created:
                    customers_created.add(row["customer_id"])
                else:
                    customers_updated.add(row["customer_id"])

                _, invoice_was_created = Invoice.objects.update_or_create(
                    invoice_number=row["invoice_number"],
                    defaults={
                        "customer": customer,
                        "amount": Decimal(row["amount_eur"]),
                        "due_date": row["due_date"],
                    },
                )
                if invoice_was_created:
                    invoices_created.add(row["invoice_number"])
                else:
                    invoices_updated.add(row["invoice_number"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Customers: {len(customers_created)} created, {len(customers_updated)} updated; "
                f"Invoices: {len(invoices_created)} created, {len(invoices_updated)} updated"
            )
        )
