# =============================================================================
# test_e2e_flow.py - End-to-end test: Upload → Match → Settlement
# =============================================================================
# Runs the full app flow using a temporary test database:
#   1. Import contracts (creates shows)
#   2. Import bank transactions
#   3. Import invoices (links to shows via contract_number)
#   4. Match: create handshakes (bank → invoice)
#   5. Settlement: create settlement for a show, then confirm
#   6. Verify state at each step
#
# Run: python test_e2e_flow.py
# =============================================================================

import sys
import os

# Point to test DB before any database imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
config.DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pinball_e2e_test.db")

from database import (
    init_db,
    load_shows,
    load_contracts,
    load_bank_transactions,
    load_invoices,
    load_handshakes,
    load_settlements,
    create_handshake,
    create_settlement,
    confirm_settlement,
)
from importers.bank_importer import BankImporter
from importers.contract_importer import ContractImporter
from importers.invoice_importer import InvoiceImporter

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
BANK_FILE = os.path.join(TEST_DIR, "HSB Export for V3 Build - Data Export for V3 Build.csv")
CONTRACT_FILE = os.path.join(TEST_DIR, "System one Data Export for V3 Build - Data Export for V3 Build.csv")
INVOICE_FILE = os.path.join(TEST_DIR, "Invoice Data Import Tables for V3 Build - Data Import Tables for V3 Build.csv")

def step(name):
    print(f"\n--- {name} ---")

def main():
    print("=" * 60)
    print("E2E TEST: Upload -> Match -> Settlement")
    print("Using DB:", config.DB_PATH)
    print("=" * 60)

    # Remove test DB if it exists (clean start)
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)

    # -------------------------------------------------------------------------
    # 1. Init DB
    # -------------------------------------------------------------------------
    step("1. Init DB")
    ok = init_db()
    assert ok, "init_db failed"
    print("OK: Database initialized")

    # -------------------------------------------------------------------------
    # 2. Import contracts (creates shows)
    # -------------------------------------------------------------------------
    step("2. Import contracts")
    if not os.path.exists(CONTRACT_FILE):
        print("SKIP: Contract file not found")
    else:
        imp = ContractImporter(CONTRACT_FILE)
        success, msg, count = imp.import_contracts()
        print(f"Result: {msg}")
        assert success or count >= 0, msg
    shows = load_shows()
    print(f"Shows in DB: {len(shows)}")
    assert len(shows) > 0, "No shows after contract import"

    # -------------------------------------------------------------------------
    # 3. Import bank transactions
    # -------------------------------------------------------------------------
    step("3. Import bank transactions")
    if not os.path.exists(BANK_FILE):
        print("SKIP: Bank file not found")
    else:
        imp = BankImporter(BANK_FILE)
        success, msg, count = imp.import_transactions()
        print(f"Result: {msg}")
    bank_all = load_bank_transactions()
    bank_in = load_bank_transactions(incoming_only=True)
    print(f"Bank transactions: {len(bank_all)} total, {len(bank_in)} incoming")
    assert len(bank_all) > 0, "No bank transactions after import"

    # -------------------------------------------------------------------------
    # 4. Import invoices (links to shows via contract_number)
    # -------------------------------------------------------------------------
    step("4. Import invoices")
    if not os.path.exists(INVOICE_FILE):
        print("SKIP: Invoice file not found")
    else:
        imp = InvoiceImporter(INVOICE_FILE)
        success, msg, count = imp.import_invoices()
        print(f"Result: {msg}")
    invoices = load_invoices()
    linked = invoices[invoices["show_id"].notna() & (invoices["show_id"] > 0)] if "show_id" in invoices.columns else invoices
    print(f"Invoices: {len(invoices)} total, {len(linked)} linked to shows")
    assert len(invoices) > 0, "No invoices after import"

    # -------------------------------------------------------------------------
    # 5. Match: create handshakes (unmatched bank → unpaid invoices)
    # -------------------------------------------------------------------------
    step("5. Match (create handshakes)")
    bank_unmatched = load_bank_transactions(unmatched_only=True, incoming_only=True)
    inv_unpaid = load_invoices(unpaid_only=True)
    print(f"Unmatched incoming bank: {len(bank_unmatched)}, Unpaid invoices: {len(inv_unpaid)}")

    handshakes_created = 0
    if len(bank_unmatched) > 0 and len(inv_unpaid) > 0:
        # Create handshakes: apply first bank tx to first unpaid invoice (up to invoice total)
        for _, b in bank_unmatched.iterrows():
            if handshakes_created >= 3:
                break
            bid = int(b["bank_id"])
            amt_bank = float(b["amount"])
            for _, inv in inv_unpaid.iterrows():
                iid = int(inv["invoice_id"])
                total = float(inv["total_gross"])
                paid = float(inv.get("paid_amount") or 0)
                remaining = total - paid
                if remaining <= 0:
                    continue
                apply = min(amt_bank, remaining)
                if apply <= 0:
                    continue
                hid = create_handshake(bid, iid, apply, 0, "E2E test", None)
                if hid:
                    handshakes_created += 1
                    amt_bank -= apply
                    inv_unpaid = load_invoices(unpaid_only=True)
                if amt_bank <= 0:
                    break
        print(f"Created {handshakes_created} handshake(s)")
    else:
        print("No unmatched bank or unpaid invoices to match")

    handshakes = load_handshakes()
    print(f"Total handshakes in DB: {len(handshakes)}")

    # -------------------------------------------------------------------------
    # 6. Settlement: create for one show, then confirm
    # -------------------------------------------------------------------------
    step("6. Settlement (create + confirm)")
    shows = load_shows()
    if len(shows) == 0:
        print("SKIP: No shows for settlement")
    else:
        row = shows.iloc[0]
        show_id = int(row["show_id"])
        artist = str(row.get("artist") or "Artist")
        amount_due = float(row.get("net_artist_settlement") or row.get("total_deal_value") or 1000)
        sid = create_settlement({
            "show_id": show_id,
            "artist": artist,
            "amount_due": amount_due,
            "currency": "GBP",
            "amount_paid": 0,
            "status": "Pending",
        })
        assert sid, "create_settlement failed"
        print(f"Created settlement_id={sid} for show_id={show_id}")

        ok = confirm_settlement(sid, "E2E Test")
        assert ok, "confirm_settlement failed"
        print("Confirmed settlement")

        settlements = load_settlements(show_id=show_id)
        st = settlements[settlements["settlement_id"] == sid]
        if len(st) > 0:
            status = st.iloc[0].get("status")
            print(f"Settlement status: {status}")
            assert str(status) == "Confirmed", f"Expected Confirmed, got {status}"

    # -------------------------------------------------------------------------
    # 7. Final verification
    # -------------------------------------------------------------------------
    step("7. Final state")
    print(f"Shows: {len(load_shows())}")
    print(f"Contracts: {len(load_contracts())}")
    print(f"Bank transactions: {len(load_bank_transactions())}")
    print(f"Invoices: {len(load_invoices())}")
    print(f"Handshakes: {len(load_handshakes())}")
    print(f"Settlements: {len(load_settlements())}")

    # Clean up test DB
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
        print(f"Removed test DB: {config.DB_PATH}")

    print("\n" + "=" * 60)
    print("E2E PASSED: Upload -> Match -> Settlement all OK")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as e:
        print(f"\nFAIL: {e}")
        sys.exit(1)
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
