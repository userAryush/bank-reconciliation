"""Generate deterministic synthetic data for the bank reconciliation project."""

import argparse
import csv
import datetime
import pathlib
import random


CUSTOMER_NAMES: list[str] = [
    "Müller Maschinenbau GmbH",
    "Schmidt & Söhne AG",
    "Weber Logistik UG",
    "Meyer Elektronik GmbH",
    "Fischer Stahlhandel GmbH",
    "Bauer Haustechnik KG",
    "Hoffmann Verpackung GmbH",
    "König Lebensmittel AG",
    "Wolf Industrieanlagen GmbH",
    "Neumann Consulting GmbH",
    "Schneider Textil GmbH",
    "Braun Medizintechnik AG",
    "Zimmermann IT Services GmbH",
    "Hartmann Gebäudetechnik UG",
    "Krüger Transporte GmbH",
    "Böhm Maschinenparts KG",
    "Jäger Werkzeugbau GmbH",
    "Seidel Kunststofftechnik AG",
    "Müller Bau GmbH",
    "Müller Metallbau GmbH",
    "Schmidt Industrietechnik GmbH",
    "Schmitt Gebäudeservice GmbH",
    "Klein & Partner GmbH",
    "Großhandel Wagner GmbH",
    "Schröder Energie GmbH",
    "Petersen Lebensmittel GmbH",
    "Huber Elektroanlagen AG",
    "Krause Sanitär GmbH",
    "Richter Software GmbH",
    "Brandt Kunststoff GmbH",
    "Köhler Werbetechnik UG",
    "Lang & Lang GmbH",
    "Maier Produktionsservice KG",
    "Engel Textilveredelung GmbH",
    "Vogel Bürobedarf AG",
    "Franke Automatisierung GmbH",
    "Becker Sicherheitstechnik GmbH",
    "Lange Garten- und Landschaftsbau GmbH",
    "Sommer Reisedienst UG",
    "Weiß Druckerei GmbH",
]


def cents_text(cents: int) -> str:
    """Format integer cents as a dot-decimal string."""
    return f"{cents // 100}.{cents % 100:02d}"


def german_amount(cents: int) -> str:
    """Format integer cents as a German decimal amount."""
    whole, fraction = divmod(cents, 100)
    return f"{whole:,}".replace(",", ".") + f",{fraction:02d}"


def invoice_text(rng: random.Random, invoice_number: str) -> str:
    """Create varied German invoice free-text wording."""
    templates = [
        "Rechnung {invoice}",
        "RE  {invoice}  vielen Dank",
        "Zahlung Rg. Nr. {invoice}",
        "Rechnungsnummer {invoice}",
        "Ihre Rechnung: {invoice}",
        "Rg {invoice} - Begleichung",
    ]
    return rng.choice(templates).format(invoice=invoice_number)


def varied_payer(rng: random.Random, customer_name: str) -> str:
    """Create a believable variation of a customer name."""
    variants = [
        customer_name.upper(),
        customer_name.replace("Müller", "Mueller").replace("Schmidt & Söhne", "Schmidt u. Soehne").replace("ß", "ss"),
        customer_name.replace(" GmbH", "").replace(" AG", "").replace(" UG", "").replace(" KG", ""),
        customer_name.replace(" GmbH", " Gmbh").replace(" AG", " A.G."),
        customer_name.replace("&", "und"),
    ]
    if "Schmidt" in customer_name:
        variants.append("Schmitt " + customer_name.split()[-1])
    if "Müller" in customer_name:
        variants.append(customer_name.replace("Müller", "Mueller"))
    if "Weber" in customer_name:
        variants.append("W. Weber")
    base = rng.choice(variants)
    if rng.random() < 0.25:
        words = base.split()
        if len(words) >= 2:
            index = rng.randrange(len(words))
            if words[index]:
                position = rng.randrange(len(words[index]))
                word = words[index]
                words[index] = word[:position] + ("x" if word[position] != "x" else "y") + word[position + 1:]
            base = " ".join(words)
    return base


def random_statement_date(rng: random.Random) -> datetime.date:
    """Select a random date from January through June 2025."""
    start = datetime.date(2025, 1, 1)
    end = datetime.date(2025, 6, 30)
    return start + datetime.timedelta(days=rng.randint(0, (end - start).days))


def write_csv(path: pathlib.Path, header: list[str], rows: list[list[str]], delimiter: str = ",") -> None:
    """Write a UTF-8 CSV with a fixed LF line ending."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=delimiter, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def generate(seed: int) -> dict[str, int]:
    """Generate invoices, bank transactions, and ground truth."""
    rng = random.Random(seed)
    data_dir = pathlib.Path(__file__).resolve().parent
    output_dir = data_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    invoices: list[dict[str, object]] = []
    start_due = datetime.date(2025, 1, 1)
    end_due = datetime.date(2025, 6, 30)

    for customer_index, customer_name in enumerate(CUSTOMER_NAMES, start=1):
        customer_id = f"CUST-{customer_index:03d}"
        for _ in range(5):
            invoice_number = f"INV-2025-{len(invoices) + 1:04d}"
            amount_cents = rng.randint(15000, 1200000)
            due_date = start_due + datetime.timedelta(days=rng.randint(0, (end_due - start_due).days))
            invoices.append({
                "invoice_number": invoice_number,
                "customer_id": customer_id,
                "customer_name": customer_name,
                "amount_cents": amount_cents,
                "due_date": due_date,
            })

    invoice_rows: list[list[str]] = []
    for invoice in invoices:
        invoice_rows.append([
            str(invoice["invoice_number"]),
            str(invoice["customer_id"]),
            str(invoice["customer_name"]),
            cents_text(int(invoice["amount_cents"])),
            invoice["due_date"].isoformat(),  # type: ignore[attr-defined]
        ])
    write_csv(
        output_dir / "open_invoices.csv",
        ["invoice_number", "customer_id", "customer_name", "amount_eur", "due_date"],
        invoice_rows,
    )

    available = list(invoices)
    rng.shuffle(available)
    paid: set[str] = set()
    transactions: list[dict[str, object]] = []

    def take_invoice() -> dict[str, object]:
        for index, invoice in enumerate(available):
            invoice_number = str(invoice["invoice_number"])
            if invoice_number not in paid:
                available.pop(index)
                paid.add(invoice_number)
                return invoice
        raise RuntimeError("Not enough unpaid invoices")

    def add_transaction(
        scenario: str,
        payer: str,
        text: str,
        amount_cents: int,
        pairs: list[tuple[str, int]],
        date: datetime.date | None = None,
    ) -> None:
        transactions.append({
            "date": date if date is not None else random_statement_date(rng),
            "payer": payer,
            "text": text,
            "amount_cents": amount_cents,
            "scenario": scenario,
            "pairs": pairs,
        })

    for _ in range(84):
        invoice = take_invoice()
        amount = int(invoice["amount_cents"])
        inv_number = str(invoice["invoice_number"])
        add_transaction(
            "exact",
            str(invoice["customer_name"]),
            invoice_text(rng, inv_number),
            amount,
            [(inv_number, amount)],
        )

    for _ in range(12):
        invoice = take_invoice()
        amount = int(invoice["amount_cents"])
        inv_number = str(invoice["invoice_number"])
        add_transaction(
            "name_variation",
            varied_payer(rng, str(invoice["customer_name"])),
            invoice_text(rng, inv_number),
            amount,
            [(inv_number, amount)],
        )

    for _ in range(10):
        invoice = take_invoice()
        original = int(invoice["amount_cents"])
        applied = (original * rng.randint(30, 70)) // 100
        inv_number = str(invoice["invoice_number"])
        add_transaction(
            "partial",
            str(invoice["customer_name"]),
            invoice_text(rng, inv_number),
            applied,
            [(inv_number, applied)],
        )

    by_customer: dict[str, list[dict[str, object]]] = {}
    for invoice in available:
        by_customer.setdefault(str(invoice["customer_name"]), []).append(invoice)

    for _ in range(6):
        eligible = [group for group in by_customer.values() if sum(str(item["invoice_number"]) not in paid for item in group) >= 2]
        if not eligible:
            raise RuntimeError("Not enough invoices for multi-invoice transactions")
        group = rng.choice(eligible)
        candidates = [item for item in group if str(item["invoice_number"]) not in paid]
        count = 3 if len(candidates) >= 3 and rng.random() < 0.45 else 2
        selected = rng.sample(candidates, count)
        for invoice in selected:
            paid.add(str(invoice["invoice_number"]))
        payer = str(selected[0]["customer_name"])
        inv_numbers = [str(invoice["invoice_number"]) for invoice in selected]
        amount = sum(int(invoice["amount_cents"]) for invoice in selected)
        spacing = " " if rng.random() < 0.5 else "  "
        text = "Rechnungen " + spacing.join(inv_numbers) + " gesammelt"
        add_transaction(
            "multi_invoice",
            payer,
            text,
            amount,
            [(inv_number, int(invoice["amount_cents"])) for inv_number, invoice in zip(inv_numbers, selected)],
        )

    for _ in range(5):
        invoice = take_invoice()
        amount = int(invoice["amount_cents"])
        inv_number = str(invoice["invoice_number"])
        text = rng.choice(["Zahlung", "Ueberweisung Maerz", "Überweisung März", "Zahlung Rechnung"])
        add_transaction(
            "missing_reference",
            str(invoice["customer_name"]),
            text,
            amount,
            [(inv_number, amount)],
        )

    duplicate_sources = [
        transaction for transaction in transactions
        if transaction["scenario"] in {"exact", "name_variation", "partial", "missing_reference"}
        and len(transaction["pairs"]) == 1  # type: ignore[arg-type]
    ]
    rng.shuffle(duplicate_sources)
    for source in duplicate_sources[:3]:
        add_transaction(
            "duplicate",
            str(source["payer"]),
            str(source["text"]),
            int(source["amount_cents"]),
            list(source["pairs"]),  # type: ignore[arg-type]
            source["date"],  # type: ignore[arg-type]
        )

    transactions.sort(key=lambda transaction: (transaction["date"], rng.random()))
    bank_rows: list[list[str]] = []
    ground_rows: list[list[str]] = []

    for tx_row, transaction in enumerate(transactions, start=1):
        bank_rows.append([
            transaction["date"].strftime("%d.%m.%Y"),  # type: ignore[union-attr]
            str(transaction["payer"]),
            str(transaction["text"]),
            german_amount(int(transaction["amount_cents"])),
        ])
        scenario = str(transaction["scenario"])
        expected_action = {
            "exact": "auto_book",
            "name_variation": "auto_book",
            "multi_invoice": "auto_book",
            "partial": "review",
            "missing_reference": "review",
            "duplicate": "reject_duplicate",
        }[scenario]
        for inv_number, amount in transaction["pairs"]:  # type: ignore[union-attr]
            ground_rows.append([
                str(tx_row),
                inv_number,
                cents_text(amount),
                scenario,
                expected_action,
            ])

    write_csv(
        output_dir / "bank_statement.csv",
        ["Buchungstag", "Auftraggeber", "Verwendungszweck", "Betrag"],
        bank_rows,
        delimiter=";",
    )
    write_csv(
        output_dir / "ground_truth.csv",
        ["tx_row", "invoice_number", "amount_applied", "scenario", "expected_action"],
        ground_rows,
    )

    counts: dict[str, int] = {
        "exact": 84,
        "name_variation": 12,
        "partial": 10,
        "multi_invoice": 6,
        "missing_reference": 5,
        "duplicate": 3,
    }
    return counts


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Generate synthetic bank reconciliation data.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    return parser.parse_args()


def main() -> None:
    """Run data generation and print the scenario summary."""
    args = parse_args()
    counts = generate(args.seed)
    print(f"Generated data with seed {args.seed}")
    for scenario, count in counts.items():
        print(f"{scenario}: {count}")


if __name__ == "__main__":
    main()
