import csv, pathlib

out = pathlib.Path("data/output")
invoices = list(csv.DictReader(open(out / "open_invoices.csv", encoding="utf-8")))
truth = list(csv.DictReader(open(out / "ground_truth.csv", encoding="utf-8")))
tx = list(csv.DictReader(open(out / "bank_statement.csv", encoding="utf-8"), delimiter=";"))

print("invoices:", len(invoices), "| transactions:", len(tx), "| truth rows:", len(truth))

inv_numbers = {r["invoice_number"] for r in invoices}
missing = [r for r in truth if r["invoice_number"] not in inv_numbers]
print("truth invoices missing from invoice file:", len(missing))

bad_rows = [r for r in truth if not (1 <= int(r["tx_row"]) <= len(tx))]
print("tx_row out of range:", len(bad_rows))

for r in truth[:3]:
    t = tx[int(r["tx_row"]) - 1]
    print(r["scenario"], "->", t["Auftraggeber"], "|", t["Verwendungszweck"], "|", t["Betrag"], "|", r["invoice_number"])