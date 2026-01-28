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
    
    print("\n" + "=" * 60)
    print("IMPORT COMPLETE!")
    print("=" * 60)
    print("\nRefresh the Pinball V3 app in your browser to see the data.")

if __name__ == "__main__":
    main()


