# =============================================================================
# database/queries.py
# =============================================================================
# PURPOSE:
#   Contains all database queries - loading and saving data.
#   This is the "data access layer" - the only code that talks to the database.
#
# WHY SEPARATE QUERIES?
#   1. Keeps SQL in one place (easy to find and modify)
#   2. Other code doesn't need to know SQL
#   3. Easy to add caching, logging, etc. later
#   4. Makes testing easier (can mock this layer)
#
# ORGANIZATION:
#   Functions are grouped by table:
#   - Shows (load_shows, create_show, etc.)
#   - Contracts (load_contracts, create_contract, etc.)
#   - Bank Transactions (load_bank_transactions, etc.)
#   - Invoices (load_invoices, etc.)
#   - And so on...
#
# NAMING CONVENTION:
#   - load_X() → Read data (SELECT)
#   - create_X() → Insert new data (INSERT)
#   - update_X() → Modify existing data (UPDATE)
#   - delete_X() → Remove data (DELETE)
#   - check_X_exists() → Check for duplicates
# =============================================================================

import pandas as pd
from datetime import datetime
import hashlib
from .connection import get_db_connection


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _generate_hash(*args):
    """
    Generate a hash from multiple values.
    Used for duplicate detection.
    
    HOW IT WORKS:
        1. Convert all arguments to strings
        2. Join them with a separator
        3. Create an MD5 hash
        4. Return the hex representation
    
    EXAMPLE:
        _generate_hash("2025-01-15", 1000.00, "Payment from ABC")
        → "a1b2c3d4e5f6..."
    
    WHY HASH?
        - Fixed length (always 32 chars)
        - Fast to compare
        - Two identical inputs = identical hash
        - Different inputs = different hash (usually)
    """
    # Convert all args to strings and join
    combined = "|".join(str(arg) for arg in args)
    # Create MD5 hash and return hex string
    return hashlib.md5(combined.encode()).hexdigest()


def _safe_float(value, default=0.0):
    """
    Safely convert a value to float.
    Returns default if conversion fails.
    
    WHY NEEDED?
        Data from CSV files can be messy:
        - Empty cells → None or ""
        - Text like "N/A" instead of numbers
        - Commas in numbers: "1,000.00"
    
    This function handles all those cases gracefully.
    """
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        # Remove commas and whitespace
        cleaned = str(value).replace(",", "").strip()
        if cleaned == "" or cleaned.lower() in ("nan", "none", "n/a", "-"):
            return default
        return float(cleaned)
    except (ValueError, TypeError):
        return default


def _safe_int(value, default=None):
    """
    Safely convert a value to integer.
    Handles numpy types from pandas DataFrames.
    """
    if value is None:
        return default
    # Handle numpy types (from pandas)
    if hasattr(value, 'item'):
        return int(value.item())
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


# =============================================================================
# SHOWS QUERIES
# =============================================================================

def load_shows(search=None, filters=None):
    """
    Load shows from the database with optional search and filters.
    
    PARAMETERS:
        search (str): Search term to filter by (searches multiple fields)
        filters (dict): Field-specific filters, e.g., {"agent": "Angelo", "status": "Contracted"}
    
    RETURNS:
        pd.DataFrame: All matching shows
    
    EXAMPLE:
        # Load all shows
        df = load_shows()
        
        # Search for "Fabric"
        df = load_shows(search="Fabric")
        
        # Filter by agent
        df = load_shows(filters={"agent": "Angelo"})
    """
    try:
        conn = get_db_connection()
        
        # Base query
        query = "SELECT * FROM shows WHERE 1=1"
        params = []
        
        # Add search condition (searches multiple fields)
        if search:
            query += """ AND (
                artist LIKE ? OR
                event_name LIKE ? OR
                venue LIKE ? OR
                promoter_name LIKE ? OR
                contract_number LIKE ?
            )"""
            search_term = f"%{search}%"
            params.extend([search_term] * 5)
        
        # Add filter conditions
        if filters:
            for field, value in filters.items():
                if value:  # Only add if value is not empty
                    query += f" AND {field} = ?"
                    params.append(value)
        
        # Order by performance date (most recent first)
        query += " ORDER BY performance_date DESC"
        
        # Execute and return as DataFrame
        df = pd.read_sql_query(query, conn, params=params if params else None)
        conn.close()
        return df
        
    except Exception as e:
        print(f"[ERROR] Error loading shows: {e}")
        return pd.DataFrame()


def load_show_by_id(show_id):
    """
    Load a single show by its ID.
    
    RETURNS:
        dict: Show data, or None if not found
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM shows WHERE show_id = ?", (show_id,))
        row = cursor.fetchone()
        
        if row:
            # Get column names
            columns = [desc[0] for desc in cursor.description]
            # Create dictionary
            show = dict(zip(columns, row))
            conn.close()
            return show
        
        conn.close()
        return None
        
    except Exception as e:
        print(f"[ERROR] Error loading show {show_id}: {e}")
        return None


def create_show(show_data):
    """
    Create a new show in the database.
    
    PARAMETERS:
        show_data (dict): Show information with keys matching column names
    
    RETURNS:
        int: The new show_id, or None if failed
    
    EXAMPLE:
        show_id = create_show({
            "contract_number": "910516",
            "artist": "Minna",
            "venue": "Fabric",
            "performance_date": "2025-11-08"
        })
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Add timestamps
        now = datetime.now().isoformat()
        show_data['created_at'] = now
        show_data['updated_at'] = now
        
        # Build INSERT statement dynamically
        columns = ", ".join(show_data.keys())
        placeholders = ", ".join(["?"] * len(show_data))
        values = list(show_data.values())
        
        cursor.execute(f"""
            INSERT INTO shows ({columns})
            VALUES ({placeholders})
        """, values)
        
        show_id = cursor.lastrowid  # Get the auto-generated ID
        conn.commit()
        conn.close()
        
        print(f"[OK] Created show #{show_id}: {show_data.get('artist', 'Unknown')}")
        return show_id
        
    except Exception as e:
        print(f"[ERROR] Error creating show: {e}")
        return None


def update_show(show_id, updates):
    """
    Update an existing show.
    
    PARAMETERS:
        show_id (int): ID of show to update
        updates (dict): Fields to update
    
    RETURNS:
        bool: True if successful
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Add updated timestamp
        updates['updated_at'] = datetime.now().isoformat()
        
        # Build UPDATE statement
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [show_id]
        
        cursor.execute(f"""
            UPDATE shows SET {set_clause}
            WHERE show_id = ?
        """, values)
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] Error updating show {show_id}: {e}")
        return False


def search_shows(query_text):
    """
    Full-text search across shows.
    Searches: artist, event, venue, promoter, contract number, notes.
    
    RETURNS:
        pd.DataFrame: Matching shows
    """
    return load_shows(search=query_text)


# =============================================================================
# CONTRACTS QUERIES
# =============================================================================

def load_contracts(search=None):
    """
    Load all contracts from the database.
    
    RETURNS:
        pd.DataFrame: All contracts
    """
    try:
        conn = get_db_connection()
        
        if search:
            query = """
                SELECT * FROM contracts 
                WHERE contract_number LIKE ? OR artist LIKE ?
                ORDER BY booking_date DESC
            """
            df = pd.read_sql_query(query, conn, params=(f"%{search}%", f"%{search}%"))
        else:
            query = "SELECT * FROM contracts ORDER BY booking_date DESC"
            df = pd.read_sql_query(query, conn)
        
        conn.close()
        return df
        
    except Exception as e:
        print(f"[ERROR] Error loading contracts: {e}")
        return pd.DataFrame()


def check_contract_exists(contract_number):
    """
    Check if a contract already exists (duplicate detection).
    
    RETURNS:
        bool: True if contract exists
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM contracts WHERE contract_number = ?",
            (contract_number,)
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
        
    except Exception as e:
        print(f"[ERROR] Error checking contract: {e}")
        return False


def create_contract(contract_data):
    """
    Create a new contract.
    
    PARAMETERS:
        contract_data (dict): Contract information
    
    RETURNS:
        int: The new contract_id, or None if failed
    """
    try:
        # Check for duplicate first
        if check_contract_exists(contract_data.get('contract_number')):
            print(f"[WARN] Contract {contract_data.get('contract_number')} already exists!")
            return None
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Add import timestamp
        contract_data['imported_at'] = datetime.now().isoformat()
        
        # Build INSERT statement
        columns = ", ".join(contract_data.keys())
        placeholders = ", ".join(["?"] * len(contract_data))
        values = list(contract_data.values())
        
        cursor.execute(f"""
            INSERT INTO contracts ({columns})
            VALUES ({placeholders})
        """, values)
        
        contract_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"[OK] Created contract #{contract_id}: {contract_data.get('contract_number')}")
        return contract_id
        
    except Exception as e:
        print(f"[ERROR] Error creating contract: {e}")
        return None


# =============================================================================
# BANK TRANSACTIONS QUERIES
# =============================================================================

def load_bank_transactions(search=None, unmatched_only=False, incoming_only=False, outgoing_only=False):
    """
    Load bank transactions.
    
    PARAMETERS:
        search (str): Search in description
        unmatched_only (bool): If True, only return unmatched transactions
        incoming_only (bool): If True, only return payments IN (amount > 0); exclude debits/paid out
        outgoing_only (bool): If True, only return payments OUT (amount < 0); for Outgoing page
    
    RETURNS:
        pd.DataFrame: Bank transactions
    """
    try:
        conn = get_db_connection()
        
        query = "SELECT * FROM bank_transactions WHERE 1=1"
        params = []
        
        if search:
            query += " AND description LIKE ?"
            params.append(f"%{search}%")
        
        if unmatched_only:
            query += " AND is_matched = 0"
        
        if incoming_only:
            query += " AND amount > 0"
        
        if outgoing_only:
            query += " AND amount < 0"
        
        query += " ORDER BY date DESC"
        
        df = pd.read_sql_query(query, conn, params=params if params else None)
        conn.close()
        return df
        
    except Exception as e:
        print(f"[ERROR] Error loading bank transactions: {e}")
        return pd.DataFrame()


def check_bank_transaction_exists(date, amount, description):
    """
    Check if a bank transaction already exists (duplicate detection).
    Uses a hash of date + amount + description.
    
    RETURNS:
        bool: True if transaction exists
    """
    try:
        # Generate hash for this transaction
        tx_hash = _generate_hash(date, amount, description)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM bank_transactions WHERE transaction_hash = ?",
            (tx_hash,)
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
        
    except Exception as e:
        print(f"[ERROR] Error checking bank transaction: {e}")
        return False


def create_bank_transaction(tx_data):
    """
    Create a new bank transaction.
    
    PARAMETERS:
        tx_data (dict): Transaction data including:
            - date, type, description, paid_out, paid_in, amount, currency
    
    RETURNS:
        int: The new bank_id, or None if failed/duplicate
    """
    try:
        # Generate hash for duplicate detection
        tx_hash = _generate_hash(
            tx_data.get('date'),
            tx_data.get('amount'),
            tx_data.get('description')
        )
        
        # Check for duplicate
        if check_bank_transaction_exists(
            tx_data.get('date'),
            tx_data.get('amount'),
            tx_data.get('description')
        ):
            print(f"[WARN] Duplicate bank transaction: {tx_data.get('description')[:30]}...")
            return None
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Add hash and timestamp
        tx_data['transaction_hash'] = tx_hash
        tx_data['imported_at'] = datetime.now().isoformat()
        
        # Build INSERT
        columns = ", ".join(tx_data.keys())
        placeholders = ", ".join(["?"] * len(tx_data))
        values = list(tx_data.values())
        
        cursor.execute(f"""
            INSERT INTO bank_transactions ({columns})
            VALUES ({placeholders})
        """, values)
        
        bank_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return bank_id
        
    except Exception as e:
        print(f"[ERROR] Error creating bank transaction: {e}")
        return None


# =============================================================================
# INVOICES QUERIES
# =============================================================================

def load_invoices(search=None, unpaid_only=False):
    """
    Load invoices from the database.
    
    PARAMETERS:
        search (str): Search in invoice number or promoter name
        unpaid_only (bool): If True, only return unpaid invoices
    
    RETURNS:
        pd.DataFrame: Invoices
    """
    try:
        conn = get_db_connection()
        
        query = "SELECT * FROM invoices WHERE 1=1"
        params = []
        
        if search:
            query += " AND (invoice_number LIKE ? OR promoter_name LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        
        if unpaid_only:
            query += " AND is_paid = 0"
        
        query += " ORDER BY invoice_date DESC"
        
        df = pd.read_sql_query(query, conn, params=params if params else None)
        conn.close()
        return df
        
    except Exception as e:
        print(f"[ERROR] Error loading invoices: {e}")
        return pd.DataFrame()


def load_invoices_with_show_details(search=None, unpaid_only=False):
    """
    Load invoices with artist and show/event details from linked show.
    Use this when you need to display artist name and show name in the UI.
    
    RETURNS:
        pd.DataFrame: Invoices with columns: all invoice columns plus
                      artist (prefers invoice.artist, falls back to show.artist),
                      event_name, venue (from shows table)
    """
    try:
        conn = get_db_connection()
        
        # Use COALESCE to prefer invoice's artist over show's artist
        query = """
            SELECT i.invoice_id, i.invoice_number, i.contract_number, i.show_id,
                   COALESCE(i.artist, s.artist) as artist,
                   i.from_entity, i.promoter_name, i.payment_bank_details,
                   i.reference, i.currency, i.total_net, i.total_vat, i.total_gross,
                   i.invoice_date, i.show_date, i.is_paid, i.paid_amount,
                   i.balance_remaining, i.import_batch, i.imported_at,
                   s.event_name,
                   s.venue
            FROM invoices i
            LEFT JOIN shows s ON i.show_id = s.show_id
            WHERE 1=1
        """
        params = []
        
        if search:
            query += " AND (i.invoice_number LIKE ? OR i.promoter_name LIKE ? OR s.artist LIKE ? OR s.event_name LIKE ? OR s.venue LIKE ?)"
            search_term = f"%{search}%"
            params.extend([search_term] * 5)
        
        if unpaid_only:
            query += " AND i.is_paid = 0"
        
        query += " ORDER BY i.invoice_date DESC"
        
        df = pd.read_sql_query(query, conn, params=params if params else None)
        conn.close()
        return df
        
    except Exception as e:
        print(f"[ERROR] Error loading invoices with show details: {e}")
        return pd.DataFrame()


def load_invoice_items(invoice_id):
    """
    Load all line items for a specific invoice.
    
    RETURNS:
        pd.DataFrame: Invoice line items
    """
    try:
        conn = get_db_connection()
        query = "SELECT * FROM invoice_items WHERE invoice_id = ? ORDER BY item_id"
        df = pd.read_sql_query(query, conn, params=(invoice_id,))
        conn.close()
        return df
        
    except Exception as e:
        print(f"[ERROR] Error loading invoice items: {e}")
        return pd.DataFrame()


def check_invoice_exists(invoice_number):
    """
    Check if an invoice already exists (duplicate detection).
    
    RETURNS:
        bool: True if invoice exists
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM invoices WHERE invoice_number = ?",
            (invoice_number,)
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
        
    except Exception as e:
        print(f"[ERROR] Error checking invoice: {e}")
        return False


def create_invoice(invoice_data, line_items=None):
    """
    Create a new invoice with optional line items.
    
    PARAMETERS:
        invoice_data (dict): Invoice header data
        line_items (list): List of line item dicts, each with:
            - account_code, description, net, vat, gross
    
    RETURNS:
        int: The new invoice_id, or None if failed/duplicate
    """
    try:
        # Check for duplicate
        invoice_number = invoice_data.get('invoice_number')
        if check_invoice_exists(invoice_number):
            print(f"[WARN] Invoice {invoice_number} already exists!")
            return None
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Add timestamp
        invoice_data['imported_at'] = datetime.now().isoformat()
        
        # Calculate balance_remaining
        invoice_data['balance_remaining'] = invoice_data.get('total_gross', 0)
        
        # Insert invoice header
        columns = ", ".join(invoice_data.keys())
        placeholders = ", ".join(["?"] * len(invoice_data))
        values = list(invoice_data.values())
        
        cursor.execute(f"""
            INSERT INTO invoices ({columns})
            VALUES ({placeholders})
        """, values)
        
        invoice_id = cursor.lastrowid
        
        # Insert line items if provided
        if line_items:
            for item in line_items:
                item['invoice_id'] = invoice_id
                item_columns = ", ".join(item.keys())
                item_placeholders = ", ".join(["?"] * len(item))
                item_values = list(item.values())
                
                cursor.execute(f"""
                    INSERT INTO invoice_items ({item_columns})
                    VALUES ({item_placeholders})
                """, item_values)
        
        conn.commit()
        conn.close()
        
        print(f"[OK] Created invoice #{invoice_id}: {invoice_number}")
        return invoice_id
        
    except Exception as e:
        print(f"[ERROR] Error creating invoice: {e}")
        return None


# =============================================================================
# OUTGOING PAYMENTS QUERIES
# =============================================================================

def load_outgoing_payments(show_id=None, payment_type=None):
    """
    Load outgoing payments.
    
    PARAMETERS:
        show_id (int): Filter by show
        payment_type (str): Filter by payment type
    
    RETURNS:
        pd.DataFrame: Outgoing payments
    """
    try:
        conn = get_db_connection()
        
        query = "SELECT * FROM outgoing_payments WHERE 1=1"
        params = []
        
        if show_id:
            query += " AND show_id = ?"
            params.append(show_id)
        
        if payment_type:
            query += " AND payment_type = ?"
            params.append(payment_type)
        
        query += " ORDER BY payment_date DESC"
        
        df = pd.read_sql_query(query, conn, params=params if params else None)
        conn.close()
        return df
        
    except Exception as e:
        print(f"[ERROR] Error loading outgoing payments: {e}")
        return pd.DataFrame()


def create_outgoing_payment(payment_data):
    """
    Record an outgoing payment (hotel, artist payment, etc.)
    
    PARAMETERS:
        payment_data (dict): Payment information
    
    RETURNS:
        int: The new payment_id, or None if failed
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Add timestamp
        payment_data['created_at'] = datetime.now().isoformat()
        
        # Build INSERT
        columns = ", ".join(payment_data.keys())
        placeholders = ", ".join(["?"] * len(payment_data))
        values = list(payment_data.values())
        
        cursor.execute(f"""
            INSERT INTO outgoing_payments ({columns})
            VALUES ({placeholders})
        """, values)
        
        payment_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"[OK] Created outgoing payment #{payment_id}: {payment_data.get('payment_type')}")
        return payment_id
        
    except Exception as e:
        print(f"[ERROR] Error creating outgoing payment: {e}")
        return None


# =============================================================================
# HANDSHAKES QUERIES (Bank ↔ Invoice Matches)
# =============================================================================

def load_handshakes(bank_id=None, invoice_id=None):
    """
    Load handshakes with joined bank and invoice details.
    
    RETURNS:
        pd.DataFrame: Handshakes with full details
    """
    try:
        conn = get_db_connection()
        
        query = """
            SELECT 
                h.handshake_id,
                h.bank_id,
                b.date as bank_date,
                b.description as bank_desc,
                b.amount as bank_amount,
                b.currency as bank_currency,
                h.invoice_id,
                i.invoice_number,
                i.promoter_name,
                i.total_gross as invoice_total,
                i.currency as invoice_currency,
                s.artist,
                s.event_name,
                s.venue,
                h.bank_amount_applied,
                h.proxy_amount,
                h.note,
                h.created_at
            FROM handshakes h
            JOIN bank_transactions b ON h.bank_id = b.bank_id
            JOIN invoices i ON h.invoice_id = i.invoice_id
            LEFT JOIN shows s ON i.show_id = s.show_id
            WHERE 1=1
        """
        params = []
        
        if bank_id:
            query += " AND h.bank_id = ?"
            params.append(bank_id)
        
        if invoice_id:
            query += " AND h.invoice_id = ?"
            params.append(invoice_id)
        
        query += " ORDER BY h.created_at DESC"
        
        df = pd.read_sql_query(query, conn, params=params if params else None)
        conn.close()
        return df
        
    except Exception as e:
        print(f"[ERROR] Error loading handshakes: {e}")
        return pd.DataFrame()


def create_handshake(bank_id, invoice_id, bank_amount_applied, proxy_amount=0, note=None, created_by=None):
    """
    Create a handshake (match) between a bank transaction and invoice.
    
    PARAMETERS:
        bank_id (int): Bank transaction ID
        invoice_id (int): Invoice ID
        bank_amount_applied (float): Amount from bank applied to this invoice
        proxy_amount (float): Adjustment amount (FX, fees, etc.)
        note (str): Explanation
        created_by (str): Who created this match
    
    RETURNS:
        int: The new handshake_id, or None if failed
    """
    try:
        # Convert types safely
        bank_id = _safe_int(bank_id)
        invoice_id = _safe_int(invoice_id)
        bank_amount_applied = _safe_float(bank_amount_applied)
        proxy_amount = _safe_float(proxy_amount)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO handshakes 
            (bank_id, invoice_id, bank_amount_applied, proxy_amount, note, created_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            bank_id,
            invoice_id,
            bank_amount_applied,
            proxy_amount,
            note,
            datetime.now().isoformat(),
            created_by
        ))
        
        handshake_id = cursor.lastrowid
        
        # Update bank transaction as matched
        cursor.execute(
            "UPDATE bank_transactions SET is_matched = 1 WHERE bank_id = ?",
            (bank_id,)
        )
        
        # Update invoice paid amount
        cursor.execute("""
            UPDATE invoices 
            SET paid_amount = paid_amount + ?,
                balance_remaining = total_gross - (paid_amount + ?),
                is_paid = CASE WHEN (paid_amount + ?) >= total_gross THEN 1 ELSE 0 END
            WHERE invoice_id = ?
        """, (bank_amount_applied + proxy_amount, bank_amount_applied + proxy_amount, 
              bank_amount_applied + proxy_amount, invoice_id))
        
        conn.commit()
        conn.close()
        
        print(f"[OK] Created handshake #{handshake_id}: Bank #{bank_id} -> Invoice #{invoice_id}")
        return handshake_id
        
    except Exception as e:
        print(f"[ERROR] Error creating handshake: {e}")
        import traceback
        traceback.print_exc()
        return None


def delete_handshake(handshake_id):
    """
    Delete a handshake and reverse its effects on invoice/bank.
    
    RETURNS:
        bool: True if successful
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get handshake details first
        cursor.execute("""
            SELECT bank_id, invoice_id, bank_amount_applied, proxy_amount
            FROM handshakes WHERE handshake_id = ?
        """, (handshake_id,))
        row = cursor.fetchone()
        
        if not row:
            print(f"[WARN] Handshake {handshake_id} not found")
            return False
        
        bank_id, invoice_id, amount_applied, proxy = row
        total_applied = amount_applied + proxy
        
        # Delete the handshake
        cursor.execute("DELETE FROM handshakes WHERE handshake_id = ?", (handshake_id,))
        
        # Check if bank transaction has other handshakes
        cursor.execute(
            "SELECT COUNT(*) FROM handshakes WHERE bank_id = ?",
            (bank_id,)
        )
        if cursor.fetchone()[0] == 0:
            # No other handshakes, mark bank as unmatched
            cursor.execute(
                "UPDATE bank_transactions SET is_matched = 0 WHERE bank_id = ?",
                (bank_id,)
            )
        
        # Reverse invoice paid amount
        cursor.execute("""
            UPDATE invoices 
            SET paid_amount = paid_amount - ?,
                balance_remaining = total_gross - (paid_amount - ?),
                is_paid = CASE WHEN (paid_amount - ?) >= total_gross THEN 1 ELSE 0 END
            WHERE invoice_id = ?
        """, (total_applied, total_applied, total_applied, invoice_id))
        
        conn.commit()
        conn.close()
        
        print(f"[OK] Deleted handshake #{handshake_id}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error deleting handshake: {e}")
        return False


# =============================================================================
# SETTLEMENTS QUERIES
# =============================================================================

def load_settlements(show_id=None, status=None):
    """
    Load settlements.
    
    RETURNS:
        pd.DataFrame: Settlements
    """
    try:
        conn = get_db_connection()
        
        query = """
            SELECT s.*, sh.artist, sh.venue, sh.performance_date
            FROM settlements s
            JOIN shows sh ON s.show_id = sh.show_id
            WHERE 1=1
        """
        params = []
        
        if show_id:
            query += " AND s.show_id = ?"
            params.append(show_id)
        
        if status:
            query += " AND s.status = ?"
            params.append(status)
        
        query += " ORDER BY s.created_at DESC"
        
        df = pd.read_sql_query(query, conn, params=params if params else None)
        conn.close()
        return df
        
    except Exception as e:
        print(f"[ERROR] Error loading settlements: {e}")
        return pd.DataFrame()


def create_settlement(settlement_data):
    """
    Create a new settlement record for artist payment.
    
    RETURNS:
        int: The new settlement_id, or None if failed
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Add timestamps
        now = datetime.now().isoformat()
        settlement_data['created_at'] = now
        settlement_data['updated_at'] = now
        
        # Calculate balance
        settlement_data['balance'] = (
            settlement_data.get('amount_due', 0) - 
            settlement_data.get('amount_paid', 0)
        )
        
        # Build INSERT
        columns = ", ".join(settlement_data.keys())
        placeholders = ", ".join(["?"] * len(settlement_data))
        values = list(settlement_data.values())
        
        cursor.execute(f"""
            INSERT INTO settlements ({columns})
            VALUES ({placeholders})
        """, values)
        
        settlement_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"[OK] Created settlement #{settlement_id}")
        return settlement_id
        
    except Exception as e:
        print(f"[ERROR] Error creating settlement: {e}")
        return None


def update_settlement(settlement_id, updates):
    """
    Update a settlement record.
    
    RETURNS:
        bool: True if successful
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Add updated timestamp
        updates['updated_at'] = datetime.now().isoformat()
        
        # Recalculate balance if amounts changed
        if 'amount_paid' in updates or 'amount_due' in updates:
            cursor.execute(
                "SELECT amount_due, amount_paid FROM settlements WHERE settlement_id = ?",
                (settlement_id,)
            )
            row = cursor.fetchone()
            if row:
                amount_due = updates.get('amount_due', row[0])
                amount_paid = updates.get('amount_paid', row[1])
                updates['balance'] = amount_due - amount_paid
                
                # Auto-update status
                if amount_paid >= amount_due:
                    updates['status'] = 'Paid'
                elif amount_paid > 0:
                    updates['status'] = 'Partial'
        
        # Build UPDATE
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [settlement_id]
        
        cursor.execute(f"""
            UPDATE settlements SET {set_clause}
            WHERE settlement_id = ?
        """, values)
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] Error updating settlement: {e}")
        return False


def confirm_settlement(settlement_id, confirmed_by):
    """
    Mark a settlement as confirmed by the team.
    
    PARAMETERS:
        settlement_id (int): Settlement to confirm
        confirmed_by (str): Name of person confirming
    
    RETURNS:
        bool: True if successful
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE settlements 
            SET status = 'Confirmed',
                confirmed_by = ?,
                confirmed_at = ?,
                updated_at = ?
            WHERE settlement_id = ?
        """, (
            confirmed_by,
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            settlement_id
        ))
        
        conn.commit()
        conn.close()
        
        print(f"[OK] Settlement #{settlement_id} confirmed by {confirmed_by}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error confirming settlement: {e}")
        return False


# =============================================================================
# LEARNING NOTES: SQL QUERY PATTERNS
# =============================================================================
#
# SELECT - Read data
#   SELECT * FROM table                    -- Get all columns
#   SELECT col1, col2 FROM table           -- Get specific columns
#   SELECT * FROM table WHERE col = value  -- Filter rows
#   SELECT * FROM table ORDER BY col DESC  -- Sort results
#
# INSERT - Add data
#   INSERT INTO table (col1, col2) VALUES (val1, val2)
#
# UPDATE - Modify data
#   UPDATE table SET col1 = val1 WHERE condition
#
# DELETE - Remove data
#   DELETE FROM table WHERE condition
#
# JOIN - Combine tables
#   SELECT * FROM table1 JOIN table2 ON table1.id = table2.foreign_id
#
# PARAMETERIZED QUERIES (? placeholders):
#   cursor.execute("SELECT * FROM table WHERE id = ?", (value,))
#   
#   WHY USE PARAMETERS?
#   1. Prevents SQL injection attacks
#   2. Handles escaping automatically
#   3. Better performance (query caching)
#
# =============================================================================

