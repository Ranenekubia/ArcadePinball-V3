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

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Import Data - Pinball V3",
    page_icon="📥",
    layout="wide"
)

# Initialize database
init_db()

# -----------------------------------------------------------------------------
# PAGE HEADER
# -----------------------------------------------------------------------------
st.title("📥 Import Data")
st.caption("Upload bank statements, contracts, and invoices")

# -----------------------------------------------------------------------------
# SECTION 1: BANK STATEMENT IMPORT
# -----------------------------------------------------------------------------
st.write("---")
st.write("### 💳 Bank Statement Import (HSBC)")
st.write("Upload your HSBC bank statement CSV file.")

# Show expected format in an expander (collapsed by default)
with st.expander("ℹ️ Expected Format", expanded=False):
    st.code("""
Date,Type,Description,Paid Out,Paid In,Currency
2025-07-18,CR,F&B OPERATING ACC ATA INV-16496,,9800,GBP
2025-10-03,,St Martins Place,800,,GBP
2025-11-27,CR,Payment for ARC/I25-000002 - Booking Fee,,2000,GBP
    """, language="csv")
    st.caption("💡 Tip: Make sure to include the Currency column!")

# File uploader for bank statements
bank_file = st.file_uploader(
    "Choose bank CSV file",
    type=['csv'],
    key="bank_upload",
    help="Upload your HSBC bank statement"
)

# Import button (only shows if file is uploaded)
if bank_file is not None:
    if st.button("🚀 Import Bank Transactions", type="primary", use_container_width=True):
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
                        st.info(f"🔄 Skipped {summary['duplicate_count']} duplicates")
                else:
                    st.error(message)
                    
            except Exception as e:
                st.error(f"❌ Import error: {str(e)}")

# -----------------------------------------------------------------------------
# SECTION 2: CONTRACT IMPORT
# -----------------------------------------------------------------------------
st.write("---")
st.write("### 📋 Contract Import (System One)")
st.write("Upload your contract/booking export from System One.")

with st.expander("ℹ️ Expected Format", expanded=False):
    st.code("""
Contract Number,Booking Date,Artist,Event,Venue,City,Country,Performance date,Performance Day,Contracted Deal,Total deal Value,AF,Hotel buyout,Ground buyout,Transport buyout,WHT,BF,BF VAT,Total Settlement for Artist
910516,2025-07-01,Minna,Hopkins Creek Festival,Taungurung Country,Lima East,Australia,2025-11-08,Saturday,AF $3400 & BF $600,825,6925,0,0,0,Zero,825,,6925
    """, language="csv")
    st.caption("💡 This will create both Contract and Show records.")

contract_file = st.file_uploader(
    "Choose contract CSV/Excel file",
    type=['csv', 'xlsx'],
    key="contract_upload",
    help="Upload your System One export"
)

if contract_file is not None:
    if st.button("🚀 Import Contracts", type="primary", use_container_width=True):
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
                st.error(f"❌ Import error: {str(e)}")

# -----------------------------------------------------------------------------
# SECTION 3: INVOICE IMPORT
# -----------------------------------------------------------------------------
st.write("---")
st.write("### 📄 Invoice Import")
st.write("Upload your invoice export CSV (long format - multiple rows per invoice).")

with st.expander("ℹ️ Expected Format", expanded=False):
    st.code("""
InvoiceNumber,Contract Number,From Entity,AccountCode,Net Amount,VAT Amount,Gross Amount,Payment Bank Details,Currency
ARC/I25-000002,BKG-2025-001,Arcade Talent Agency Ltd,Booking Fee,2000,0,2000,Arcade Account,GBP
ARC/I25-000002,BKG-2025-001,Arcade Talent Agency Ltd,Artist Fee,4000,0,4000,Arcade Account,GBP
ARC/I25-000003,BKG-2025-002,Arcade Talent Agency Ltd,Booking Fee,800,160,960,Arcade Account,GBP
    """, language="csv")
    st.caption("💡 Multiple rows with the same InvoiceNumber will be grouped together.")

invoice_file = st.file_uploader(
    "Choose invoice CSV file",
    type=['csv'],
    key="invoice_upload",
    help="Upload your invoice export"
)

if invoice_file is not None:
    if st.button("🚀 Import Invoices", type="primary", use_container_width=True):
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
                st.error(f"❌ Import error: {str(e)}")

# -----------------------------------------------------------------------------
# SECTION 4: CURRENT DATA SUMMARY
# -----------------------------------------------------------------------------
st.write("---")
st.write("### 📋 Current Data")

# Load current counts
bank_df = load_bank_transactions()
contracts_df = load_contracts()
invoices_df = load_invoices()
shows_df = load_shows()

# Display in columns
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("💳 Bank Transactions", len(bank_df))
    if len(bank_df) > 0:
        st.dataframe(
            bank_df[['date', 'description', 'amount', 'currency']].head(3),
            use_container_width=True,
            hide_index=True
        )

with col2:
    st.metric("📋 Contracts", len(contracts_df))
    if len(contracts_df) > 0:
        st.dataframe(
            contracts_df[['contract_number', 'artist', 'performance_date']].head(3),
            use_container_width=True,
            hide_index=True
        )

with col3:
    st.metric("📄 Invoices", len(invoices_df))
    if len(invoices_df) > 0:
        st.dataframe(
            invoices_df[['invoice_number', 'total_gross', 'currency']].head(3),
            use_container_width=True,
            hide_index=True
        )

with col4:
    st.metric("🎭 Shows", len(shows_df))
    if len(shows_df) > 0:
        st.dataframe(
            shows_df[['artist', 'venue', 'performance_date']].head(3),
            use_container_width=True,
            hide_index=True
        )

# -----------------------------------------------------------------------------
# SECTION 5: DATA MANAGEMENT
# -----------------------------------------------------------------------------
st.write("---")
st.write("### 🗑️ Data Management")
st.warning("⚠️ These actions cannot be undone! Use with caution.")

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
        st.success(f"✅ {display_name} cleared!")
        st.session_state[confirm_key] = False
        st.rerun()
    else:
        # First click - ask for confirmation
        st.session_state[confirm_key] = True
        st.warning("⚠️ Click again to confirm")

with col1:
    if st.button("🗑️ Clear Bank Data", type="secondary", use_container_width=True):
        confirm_and_clear('bank', ['bank_transactions'], 'Bank transactions')

with col2:
    if st.button("🗑️ Clear Contracts", type="secondary", use_container_width=True):
        confirm_and_clear('contracts', ['contracts'], 'Contracts')

with col3:
    if st.button("🗑️ Clear Invoices", type="secondary", use_container_width=True):
        confirm_and_clear('invoices', ['invoice_items', 'invoices'], 'Invoices')

with col4:
    if st.button("🗑️ Clear ALL Data", type="secondary", use_container_width=True):
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


