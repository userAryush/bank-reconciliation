# Synthetic Bank Reconciliation Data

## Files

### `open_invoices.csv`

Comma-separated UTF-8 invoice data.

- `invoice_number`: Unique invoice number in the form `INV-2025-0001`.
- `customer_id`: Customer identifier in the form `CUST-001`.
- `customer_name`: A realistic German company name.
- `amount_eur`: Invoice amount in euros, written with dot decimals.
- `due_date`: Due date in ISO `YYYY-MM-DD` format.

There are 200 invoices for 40 customers. Each customer has five invoices with due dates between January and June 2025.

### `bank_statement.csv`

Semicolon-separated UTF-8 bank statement data. It contains 120 transactions sorted by `Buchungstag`.

- `Buchungstag`: Booking date in `dd.mm.yyyy` format.
- `Auftraggeber`: Payer or sender name.
- `Verwendungszweck`: Free-text payment purpose.
- `Betrag`: Positive payment amount with a German thousands separator and decimal comma.

### `ground_truth.csv`

Comma-separated UTF-8 labels for transaction-invoice pairs.

- `tx_row`: 1-based transaction position after sorting in `bank_statement.csv`.
- `invoice_number`: Invoice associated with the bank transaction. For duplicate rows, this is the invoice paid by the original transaction.
- `amount_applied`: Amount applied to the invoice, written with dot decimals.
- `scenario`: One of `exact`, `name_variation`, `partial`, `multi_invoice`, `missing_reference`, or `duplicate`.
- `expected_action`: `auto_book`, `review`, or `reject_duplicate`.

## Scenarios

- `exact`: 84 transactions (70%). Correct amount, correct customer name, and invoice number in the text.
- `name_variation`: 12 transactions (10%). Invoice number present, but the customer name is altered.
- `partial`: 10 transactions (8.33%). The text contains the invoice number and the payment covers 30–70% of the invoice amount.
- `multi_invoice`: 6 transactions (5%). One payment covers 2–3 invoices from the same customer.
- `missing_reference`: 5 transactions (4.17%). Correct customer and amount, but no invoice number in the text.
- `duplicate`: 3 transactions (2.50%). Exact copies of earlier transactions.

Exact, name-variation, and multi-invoice rows have `auto_book` as their expected action. Partial and missing-reference rows require `review`. Duplicate rows require `reject_duplicate`.

## Regenerate

Run the generator from the project root:

```powers
python data/generate_data.py
```

The default seed is `42`. Override it with:

```powers
python data/generate_data.py --seed 123
```

The generator uses a local `random.Random` instance and writes all three CSV files to `data/output/`. The same seed recreates byte-identical CSV files.
