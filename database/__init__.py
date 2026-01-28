# =============================================================================
# database/__init__.py
# =============================================================================
# PURPOSE:
#   Makes the database folder a Python package and provides easy imports.
#   
# USAGE:
#   Instead of writing:
#       from database.connection import get_db_connection
#       from database.schema import init_db
#       from database.queries import load_shows
#   
#   You can write:
#       from database import get_db_connection, init_db, load_shows
#
# HOW IT WORKS:
#   We import functions from submodules and "re-export" them here.
#   This is a common Python pattern for cleaner imports.
# =============================================================================

# Import from connection module
from .connection import get_db_connection

# Import from schema module
from .schema import init_db, get_table_info

# Import from queries module - all the data loading/saving functions
from .queries import (
    # Shows
    load_shows,
    load_show_by_id,
    create_show,
    update_show,
    search_shows,
    
    # Contracts
    load_contracts,
    create_contract,
    check_contract_exists,
    
    # Bank Transactions
    load_bank_transactions,
    create_bank_transaction,
    check_bank_transaction_exists,
    
    # Invoices
    load_invoices,
    load_invoice_items,
    create_invoice,
    check_invoice_exists,
    
    # Outgoing Payments
    load_outgoing_payments,
    create_outgoing_payment,
    
    # Handshakes (matches between bank and invoices)
    load_handshakes,
    create_handshake,
    delete_handshake,
    
    # Settlements
    load_settlements,
    create_settlement,
    update_settlement,
    confirm_settlement,
)


