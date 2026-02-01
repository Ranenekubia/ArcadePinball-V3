# =============================================================================
# pages/2_📥_Import.py
# =============================================================================
# PURPOSE:
#   Data import page - upload bank statements, contracts, and invoices.
#   This is where all external data enters the system.
#
# WHAT IT DOES:
#   1. Bank Statement Import (HSBC format)
#   2. Contract Import (System One format)
#   3. Invoice Import (CSV with line items)
#   4. Shows import history and current counts
#   5. Provides data management (clear) options
#
# DUPLICATE DETECTION:
#   Each importer checks for duplicates before inserting:
#   - Bank: Hash of date + amount + description
#   - Contracts: Contract number must be unique
#   - Invoices: Invoice number must be unique
# =============================================================================

import streamlit as st
import sqlite3
from database import (
    init_db,
    load_bank_transactions,
    load_invoices,
    load_contracts,
    load_shows
)
from importers import BankImporter, ContractImporter, InvoiceImporter
from config import DB_PATH
from utils.styling import apply_minimal_style

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Import Data - Pinball V3",
    page_icon="📥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply minimal styling
apply_minimal_style()

# Initialize database
init_db()

# -----------------------------------------------------------------------------
# PAGE HEADER
# -----------------------------------------------------------------------------
st.title("Import Data")
st.caption("Upload bank statements, contracts, and invoices")

# -----------------------------------------------------------------------------
# SECTION 1: BANK STATEMENT IMPORT
# -----------------------------------------------------------------------------
st.write("---")
st.write("### Bank Statement Import")
st.write("Upload your HSBC bank statement CSV file.")

# Show expected format in an expander (collapsed by default)
with st.expander("Expected Format", expanded=False):
    st.code("""
Date,Type,Description,Paid Out,Paid In,Currency
2025-07-18,CR,F&B OPERATING ACC ATA INV-16496,,9800,GBP
2025-10-03,,St Martins Place,800,,GBP
2025-11-27,CR,Payment for ARC/I25-000002 - Booking Fee,,2000,GBP
    """, language="csv")
    st.caption("Tip: Make sure to include the Currency column")

# File uploader for bank statements
bank_file = st.file_uploader(
    "Choose bank CSV file",
    type=['csv'],
    key="bank_upload",
    help="Upload your HSBC bank statement"
)

# Import button (only shows if file is uploaded)
if bank_file is not None:
    if st.button("Import Bank Transactions", type="primary", use_container_width=True):
        with st.spinner("Importing bank transactions..."):
            try:
                # Create importer and run import
                importer = BankImporter(bank_file)
                success, message, count = importer.import_transactions()
                
                if success:
                    st.success(message)
                    st.balloons()  # Celebration animation!
                    
                    # Show details
                    summary = importer.get_import_summary()
                    if summary['duplicate_count'] > 0:
                        st.info(f"Skipped {summary['duplicate_count']} duplicates")
                else:
                    st.error(message)
                    
            except Exception as e:
                st.error(f"Import error: {str(e)}")

# -----------------------------------------------------------------------------
# SECTION 2: CONTRACT IMPORT
# -----------------------------------------------------------------------------
st.write("---")
st.write("### Contract Import")
st.write("Upload your contract/booking export from System One.")

with st.expander("Expected Format", expanded=False):
    st.code("""
Contract Number,Booking Date,Artist,Event,Venue,City,Country,Performance date,Performance Day,Contracted Deal,Total deal Value,AF,Hotel buyout,Ground buyout,Transport buyout,WHT,BF,BF VAT,Total Settlement for Artist
910516,2025-07-01,Minna,Hopkins Creek Festival,Taungurung Country,Lima East,Australia,2025-11-08,Saturday,AF $3400 & BF $600,825,6925,0,0,0,Zero,825,,6925
    """, language="csv")
    st.caption("This will create both Contract and Show records")

contract_file = st.file_uploader(
    "Choose contract CSV/Excel file",
    type=['csv', 'xlsx'],
    key="contract_upload",
    help="Upload your System One export"
)

if contract_file is not None:
    if st.button("Import Contracts", type="primary", use_container_width=True):
        with st.spinner("Importing contracts..."):
            try:
                importer = ContractImporter(contract_file)
                success, message, count = importer.import_contracts()
                
                if success:
                    st.success(message)
                    st.balloons()
                else:
                    st.error(message)
                    
            except Exception as e:
                st.error(f"Import error: {str(e)}")

# -----------------------------------------------------------------------------
# SECTION 3: INVOICE IMPORT
# -----------------------------------------------------------------------------
st.write("---")
st.write("### Invoice Import")
st.write("Upload your invoice export CSV (long format - multiple rows per invoice).")

with st.expander("Expected Format", expanded=False):
    st.code("""
InvoiceNumber,Contract Number,From Entity,AccountCode,Net Amount,VAT Amount,Gross Amount,Payment Bank Details,Currency
ARC/I25-000002,BKG-2025-001,Arcade Talent Agency Ltd,Booking Fee,2000,0,2000,Arcade Account,GBP
ARC/I25-000002,BKG-2025-001,Arcade Talent Agency Ltd,Artist Fee,4000,0,4000,Arcade Account,GBP
ARC/I25-000003,BKG-2025-002,Arcade Talent Agency Ltd,Booking Fee,800,160,960,Arcade Account,GBP
    """, language="csv")
    st.caption("Multiple rows with the same InvoiceNumber will be grouped together")

invoice_file = st.file_uploader(
    "Choose invoice CSV file",
    type=['csv'],
    key="invoice_upload",
    help="Upload your invoice export"
)

if invoice_file is not None:
    if st.button("Import Invoices", type="primary", use_container_width=True):
        with st.spinner("Importing invoices..."):
            try:
                importer = InvoiceImporter(invoice_file)
                success, message, count = importer.import_invoices()
                
                if success:
                    st.success(message)
                    st.balloons()
                else:
                    st.error(message)
                    
            except Exception as e:
                st.error(f"Import error: {str(e)}")

# -----------------------------------------------------------------------------
# SECTION 4: CURRENT DATA SUMMARY (full schema / all columns)
# -----------------------------------------------------------------------------

# Full-screen state key
FULLSCREEN_KEY = "import_full_screen"
MAX_PREVIEW_ROWS = 50

# Load current data (all columns)
bank_df = load_bank_transactions()
contracts_df = load_contracts()
invoices_df = load_invoices()
shows_df = load_shows()

fullscreen_titles = {
    "bank": "Bank transactions",
    "contracts": "Contracts",
    "invoices": "Invoices",
    "shows": "Shows",
}
dfs = {"bank": bank_df, "contracts": contracts_df, "invoices": invoices_df, "shows": shows_df}

# ============================================================================
# FULL-SCREEN MODE: Show only the selected table, nothing else
# ============================================================================
current_full = st.session_state.get(FULLSCREEN_KEY)
if current_full:
    title = fullscreen_titles.get(current_full, current_full)
    full_df = dfs.get(current_full)

    # Header with Exit button
    col_title, col_exit = st.columns([5, 1])
    with col_title:
        st.title(f"📺 {title} — Full Screen")
    with col_exit:
        if st.button("✕ Exit", key="exit_fullscreen", use_container_width=True):
            st.session_state.pop(FULLSCREEN_KEY, None)
            st.rerun()

    st.write("---")

    # Show full dataframe with large height (all rows, all columns)
    if full_df is not None and len(full_df) > 0:
        st.dataframe(full_df, height=700, use_container_width=True, hide_index=True)
        st.caption(f"Showing all {len(full_df)} rows and all columns.")
    else:
        st.info(f"No data in {title} yet.")

    # Stop here - don't render the rest of the page
    st.stop()

# ============================================================================
# NORMAL MODE: Show expanders with preview and "View full screen" buttons
# ============================================================================
st.write("---")
st.write("### Current Data")
st.caption("Full schema shown for each table. Click **View full screen** to see all data. Invoices link to shows via **contract_number**.")

def _open_fullscreen(table_key):
    st.session_state[FULLSCREEN_KEY] = table_key

with st.expander("Bank transactions — all columns", expanded=False):
    st.metric("Count", len(bank_df))
    if len(bank_df) > 0:
        if st.button("View full screen", key="fs_bank", use_container_width=True):
            _open_fullscreen("bank")
            st.rerun()
        st.dataframe(bank_df.head(MAX_PREVIEW_ROWS), use_container_width=True, hide_index=True)
    else:
        st.info("No bank transactions yet. Import a bank CSV above.")

with st.expander("Contracts — all columns", expanded=False):
    st.metric("Count", len(contracts_df))
    if len(contracts_df) > 0:
        if st.button("View full screen", key="fs_contracts", use_container_width=True):
            _open_fullscreen("contracts")
            st.rerun()
        st.dataframe(contracts_df.head(MAX_PREVIEW_ROWS), use_container_width=True, hide_index=True)
    else:
        st.info("No contracts yet. Import a contract CSV above.")

with st.expander("Invoices — all columns", expanded=True):
    st.metric("Count", len(invoices_df))
    if len(invoices_df) > 0:
        if st.button("View full screen", key="fs_invoices", use_container_width=True):
            _open_fullscreen("invoices")
            st.rerun()
        st.dataframe(invoices_df.head(MAX_PREVIEW_ROWS), use_container_width=True, hide_index=True)
    else:
        st.info("No invoices yet. Import an invoice CSV above. Use the same **contract_number** as in your contract/show import so invoices attach to the correct show.")

with st.expander("Shows — all columns", expanded=False):
    st.metric("Count", len(shows_df))
    if len(shows_df) > 0:
        if st.button("View full screen", key="fs_shows", use_container_width=True):
            _open_fullscreen("shows")
            st.rerun()
        st.dataframe(shows_df.head(MAX_PREVIEW_ROWS), use_container_width=True, hide_index=True)
    else:
        st.info("No shows yet. Import contracts first; each contract creates a show with the same contract_number.")

# -----------------------------------------------------------------------------
# SECTION 5: DATA MANAGEMENT
# -----------------------------------------------------------------------------
st.write("---")
st.write("### Data Management")
st.warning("These actions cannot be undone. Use with caution.")

col1, col2, col3, col4 = st.columns(4)

# Helper function for confirmation pattern
def confirm_and_clear(key, table_names, display_name):
    """
    Two-click confirmation pattern for clearing data.
    First click sets a flag, second click actually clears.
    """
    confirm_key = f'confirm_clear_{key}'
    
    if st.session_state.get(confirm_key, False):
        # Second click - actually clear
        conn = sqlite3.connect(DB_PATH)
        for table in table_names:
            conn.execute(f"DELETE FROM {table}")
        conn.commit()
        conn.close()
        st.success(f"{display_name} cleared")
        st.session_state[confirm_key] = False
        st.rerun()
    else:
        # First click - ask for confirmation
        st.session_state[confirm_key] = True
        st.warning("Click again to confirm")

with col1:
    if st.button("Clear Bank Data", type="secondary", use_container_width=True):
        confirm_and_clear('bank', ['bank_transactions'], 'Bank transactions')

with col2:
    if st.button("Clear Contracts", type="secondary", use_container_width=True):
        confirm_and_clear('contracts', ['contracts'], 'Contracts')

with col3:
    if st.button("Clear Invoices", type="secondary", use_container_width=True):
        confirm_and_clear('invoices', ['invoice_items', 'invoices'], 'Invoices')

with col4:
    if st.button("Clear All Data", type="secondary", use_container_width=True):
        confirm_and_clear('all', [
            'handshakes', 'settlements', 'outgoing_payments',
            'invoice_items', 'invoices', 'contracts',
            'bank_transactions', 'shows'
        ], 'All data')


# =============================================================================
# LEARNING NOTES: FILE UPLOADS IN STREAMLIT
# =============================================================================
#
# st.file_uploader():
#   Creates a file upload widget. Returns a file-like object or None.
#   
#   file = st.file_uploader("Label", type=['csv', 'xlsx'])
#   
#   - type: List of allowed file extensions
#   - key: Unique identifier (needed if multiple uploaders)
#   - help: Tooltip text
#
# WORKING WITH UPLOADED FILES:
#   The returned object can be:
#   - Passed directly to pandas: pd.read_csv(file)
#   - Read as bytes: file.read()
#   - Read as string: file.getvalue().decode('utf-8')
#
# IMPORTANT:
#   - File is in memory, not saved to disk
#   - File object can only be read once (need to reset with file.seek(0))
#   - After page refresh, file is gone (user must re-upload)
#
# =============================================================================


