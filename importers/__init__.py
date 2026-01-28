# =============================================================================
# importers/__init__.py
# =============================================================================
# PURPOSE:
#   Makes the importers folder a Python package and provides easy imports.
#   
# WHAT ARE IMPORTERS?
#   Importers are classes that:
#   1. Read data from external files (CSV, Excel)
#   2. Parse and validate the data
#   3. Transform it to match our database schema
#   4. Save it to the database
#   5. Handle errors and duplicates gracefully
#
# AVAILABLE IMPORTERS:
#   - BankImporter: Imports HSBC bank statement CSVs
#   - ContractImporter: Imports System One contract exports
#   - InvoiceImporter: Imports invoice CSVs with line items
# =============================================================================

from .bank_importer import BankImporter
from .contract_importer import ContractImporter
from .invoice_importer import InvoiceImporter


