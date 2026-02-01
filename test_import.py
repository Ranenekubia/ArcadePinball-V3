# =============================================================================
# test_import.py - Quick test script to import test data
# =============================================================================
# This script imports the test data files directly without using the UI.
# Run this from the command line to populate the database with test data.
# =============================================================================

import sys
import os

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.schema import init_db
from database.queries import load_invoices, load_shows
from importers.bank_importer import BankImporter
from importers.contract_importer import ContractImporter
from importers.invoice_importer import InvoiceImporter

# Test data file paths
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "")

BANK_FILE = os.path.join(TEST_DATA_DIR, "HSB Export for V3 Build - Data Export for V3 Build.csv")
CONTRACT_FILE = os.path.join(TEST_DATA_DIR, "System one Data Export for V3 Build - Data Export for V3 Build.csv")
INVOICE_FILE = os.path.join(TEST_DATA_DIR, "Invoice Data Import Tables for V3 Build - Data Import Tables for V3 Build.csv")

def main():
    print("=" * 60)
    print("PINBALL V3 - TEST DATA IMPORT")
    print("=" * 60)
    
    # Initialize database
    print("\n[1] Initializing database...")
    init_db()
    print("    Database initialized!")
    
    # Import contracts first (creates shows)
    print("\n[2] Importing contracts...")
    if os.path.exists(CONTRACT_FILE):
        importer = ContractImporter(CONTRACT_FILE)
        success, message, count = importer.import_contracts()
        print(f"    Result: {message}")
    else:
        print(f"    ERROR: File not found: {CONTRACT_FILE}")
    
    # Import bank transactions
    print("\n[3] Importing bank transactions...")
    if os.path.exists(BANK_FILE):
        importer = BankImporter(BANK_FILE)
        success, message, count = importer.import_transactions()
        print(f"    Result: {message}")
    else:
        print(f"    ERROR: File not found: {BANK_FILE}")
    
    # Import invoices
    print("\n[4] Importing invoices...")
    if os.path.exists(INVOICE_FILE):
        importer = InvoiceImporter(INVOICE_FILE)
        success, message, count = importer.import_invoices()
        print(f"    Result: {message}")
    else:
        print(f"    ERROR: File not found: {INVOICE_FILE}")
    
    # Verify invoice→show link by contract_number
    print("\n[5] Verifying invoice->show link (contract_number)...")
    invoices_df = load_invoices()
    shows_df = load_shows()
    if len(invoices_df) == 0:
        print("    No invoices to verify.")
    elif len(shows_df) == 0:
        print("    No shows in DB; import contracts first so invoices can link.")
    else:
        show_contracts = set()
        if "contract_number" in shows_df.columns:
            for v in shows_df["contract_number"].dropna():
                show_contracts.add(str(v).strip())
        linked = 0
        unlinked = 0
        for _, row in invoices_df.iterrows():
            cnum = row.get("contract_number")
            if cnum is None or (isinstance(cnum, float) and (cnum != cnum or cnum == 0)):
                continue
            cnum = str(cnum).strip()
            if not cnum or cnum not in show_contracts:
                continue
            sid = row.get("show_id")
            if sid is not None and str(sid) != "nan" and int(float(sid)) > 0:
                linked += 1
            else:
                unlinked += 1
        print(f"    Invoices with matching contract_number: {linked} linked to show, {unlinked} not linked")
        if unlinked > 0 and linked == 0:
            print("    WARNING: No invoices linked to shows. Check that contract_number matches between contract and invoice CSVs.")
        elif linked > 0:
            print("    OK: At least one invoice attached to show via contract_number.")

    print("\n" + "=" * 60)
    print("IMPORT COMPLETE!")
    print("=" * 60)
    print("\nRefresh the Pinball V3 app in your browser to see the data.")

if __name__ == "__main__":
    main()


