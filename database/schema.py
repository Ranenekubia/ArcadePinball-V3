# =============================================================================
# database/schema.py
# =============================================================================
# PURPOSE:
#   Defines the DATABASE SCHEMA - the structure of all tables.
#   This is like the "blueprint" for how data is organized.
#
# WHAT IS A SCHEMA?
#   A schema defines:
#   - What tables exist
#   - What columns each table has
#   - What data types each column holds
#   - Relationships between tables (foreign keys)
#   - Constraints (rules like "this can't be empty")
#
# V3 "PINBALL" DATA MODEL:
#   The central concept is a SHOW. Everything connects to a show:
#   
#   [SHOWS] ←── Central hub, one row per gig/performance
#      ↑
#      ├── [CONTRACTS] ←── The deal/agreement for the show
#      ├── [INVOICES] ←── Bills we send to promoters
#      │      └── [INVOICE_ITEMS] ←── Line items on each invoice
#      ├── [BANK_TRANSACTIONS] ←── Money coming IN (payments received)
#      ├── [OUTGOING_PAYMENTS] ←── Money going OUT (hotels, artist payments)
#      ├── [HANDSHAKES] ←── Links between bank transactions and invoices
#      └── [SETTLEMENTS] ←── Final artist payment records
#
# WHY THIS STRUCTURE?
#   - Shows are the "anchor" - everything relates to a show
#   - One show can have multiple invoices (deposit, balance, extras)
#   - One show can have multiple bank payments (partial payments)
#   - One show can have multiple outgoing payments (hotel, flights, artist fee)
#   - This allows complete financial tracking per show
# =============================================================================

from .connection import get_db_connection


def init_db():
    """
    Initialize the database by creating all tables.
    
    WHAT THIS DOES:
        1. Connects to the database
        2. Creates each table IF it doesn't already exist
        3. Creates indexes for faster searching
        4. Commits the changes
    
    SAFE TO CALL MULTIPLE TIMES:
        "CREATE TABLE IF NOT EXISTS" means:
        - If table doesn't exist → create it
        - If table already exists → do nothing (no error)
        
        This is called "idempotent" - running it multiple times
        has the same effect as running it once.
    
    RETURNS:
        bool: True if successful, False if error
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # =====================================================================
        # TABLE 1: SHOWS (The Central Hub)
        # =====================================================================
        # This is the MAIN table. Every show/gig/performance gets one row.
        # All other tables link back to this via show_id.
        #
        # Think of this as the "master record" for each booking.
        # =====================================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shows (
                -- Primary Key: Unique identifier for each show
                -- AUTOINCREMENT means SQLite assigns 1, 2, 3... automatically
                show_id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- Contract reference (links to contracts table)
                -- Can be NULL if show added before contract imported
                contract_number TEXT,
                
                -- Who booked this show?
                agent TEXT,
                
                -- Who is performing?
                artist TEXT NOT NULL,
                
                -- Event details
                event_name TEXT,
                venue TEXT,
                city TEXT,
                country TEXT,
                
                -- When was it booked and when does it happen?
                booking_date TEXT,
                performance_date TEXT,
                performance_day TEXT,  -- e.g., "Saturday"
                
                -- The deal structure (free text, e.g., "AF $3400 & BF $600")
                deal_description TEXT,
                
                -- Financial summary (calculated from invoices/payments)
                total_deal_value REAL DEFAULT 0,
                currency TEXT DEFAULT 'GBP',  -- Deal currency (GBP, EUR, USD)
                artist_fee REAL DEFAULT 0,
                booking_fee REAL DEFAULT 0,
                
                -- Buyouts and deductions
                hotel_buyout REAL DEFAULT 0,
                flight_buyout REAL DEFAULT 0,
                ground_transport_buyout REAL DEFAULT 0,
                withholding_tax REAL DEFAULT 0,
                
                -- What the artist should ultimately receive
                net_artist_settlement REAL DEFAULT 0,
                
                -- Promoter info
                promoter_name TEXT,
                promoter_email TEXT,
                promoter_phone TEXT,
                
                -- Status tracking
                status TEXT DEFAULT 'Contracted',
                settlement_status TEXT DEFAULT 'Pending',
                
                -- Notes
                notes TEXT,
                
                -- Timestamps
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # =====================================================================
        # TABLE 2: CONTRACTS (System One Import)
        # =====================================================================
        # Contracts come from your booking system (System One).
        # Each contract defines the terms of a show.
        # A contract links to a show via contract_number.
        # =====================================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contracts (
                contract_id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- The unique contract reference (e.g., "910516")
                -- This is how we link to shows
                contract_number TEXT NOT NULL UNIQUE,
                
                -- Booking details
                booking_date TEXT,
                artist TEXT,
                event_name TEXT,
                venue TEXT,
                city TEXT,
                country TEXT,
                performance_date TEXT,
                performance_day TEXT,
                
                -- Deal terms
                deal_description TEXT,
                total_deal_value REAL,
                currency TEXT DEFAULT 'GBP',  -- Deal currency
                artist_fee REAL,
                booking_fee REAL,
                booking_fee_vat REAL,
                
                -- Buyouts
                hotel_buyout REAL DEFAULT 0,
                flight_buyout REAL DEFAULT 0,
                ground_transport_buyout REAL DEFAULT 0,
                
                -- Tax
                withholding_tax REAL DEFAULT 0,
                withholding_tax_rate REAL,
                
                -- Calculated settlement amount
                total_artist_settlement REAL,
                
                -- Import tracking
                import_batch TEXT,
                imported_at TEXT,
                
                -- Link to show (set after matching)
                show_id INTEGER,
                FOREIGN KEY(show_id) REFERENCES shows(show_id)
            )
        """)
        
        # =====================================================================
        # TABLE 3: BANK_TRANSACTIONS (HSBC Import)
        # =====================================================================
        # These are payments coming INTO the agency bank account.
        # Usually payments from promoters for shows.
        # =====================================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bank_transactions (
                bank_id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- Transaction details
                date TEXT NOT NULL,
                type TEXT,  -- e.g., "CR" for credit
                description TEXT NOT NULL,
                
                -- Money amounts (one will be filled, other will be 0)
                paid_out REAL DEFAULT 0,  -- Money leaving account
                paid_in REAL DEFAULT 0,   -- Money entering account
                
                -- Net amount (positive = money in, negative = money out)
                amount REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'GBP',
                
                -- Duplicate detection hash
                -- We create a hash of date+amount+description to detect dupes
                transaction_hash TEXT,
                
                -- Is this matched to invoices yet?
                is_matched INTEGER DEFAULT 0,  -- 0=No, 1=Yes
                
                -- Optional: Link to a show (if we can identify which show)
                show_id INTEGER,
                
                -- Import tracking
                import_batch TEXT,
                imported_at TEXT,
                
                FOREIGN KEY(show_id) REFERENCES shows(show_id)
            )
        """)
        
        # =====================================================================
        # TABLE 4: INVOICES (Invoice Import)
        # =====================================================================
        # Invoices we send to promoters.
        # One show can have multiple invoices (deposit, balance, extras).
        # =====================================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- Invoice number (UNIQUE - prevents duplicates!)
                invoice_number TEXT NOT NULL UNIQUE,
                
                -- Link to contract and show
                contract_number TEXT,
                show_id INTEGER,
                
                -- Who sent it and who receives it
                from_entity TEXT,
                promoter_name TEXT,
                
                -- Payment details
                payment_bank_details TEXT,
                reference TEXT,
                currency TEXT NOT NULL DEFAULT 'GBP',
                
                -- Totals (sum of all line items)
                total_net REAL DEFAULT 0,
                total_vat REAL DEFAULT 0,
                total_gross REAL NOT NULL,
                
                -- Dates
                invoice_date TEXT,
                show_date TEXT,
                
                -- Status
                is_paid INTEGER DEFAULT 0,  -- 0=No, 1=Yes
                paid_amount REAL DEFAULT 0,
                balance_remaining REAL,
                
                -- Import tracking
                import_batch TEXT,
                imported_at TEXT,
                
                FOREIGN KEY(show_id) REFERENCES shows(show_id)
            )
        """)
        
        # =====================================================================
        # TABLE 5: INVOICE_ITEMS (Line Items)
        # =====================================================================
        # Each invoice can have multiple line items.
        # Example: Booking Fee £500, Artist Fee £2000, VAT £100
        # =====================================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoice_items (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- Which invoice does this belong to?
                invoice_id INTEGER NOT NULL,
                
                -- What type of charge?
                account_code TEXT NOT NULL,  -- e.g., "Booking Fee", "Artist Fee"
                description TEXT,
                
                -- Amounts
                net REAL,
                vat REAL,
                gross REAL,
                
                FOREIGN KEY(invoice_id) REFERENCES invoices(invoice_id)
            )
        """)
        
        # =====================================================================
        # TABLE 6: OUTGOING_PAYMENTS (Money Going Out)
        # =====================================================================
        # Payments the agency makes: artist fees, hotels, flights, etc.
        # This tracks what we've paid OUT for each show.
        # =====================================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS outgoing_payments (
                payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- Which show is this for?
                show_id INTEGER,
                
                -- Payment details
                payment_type TEXT NOT NULL,  -- e.g., "Hotel", "Artist Advance"
                description TEXT,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'GBP',
                
                -- When was it paid?
                payment_date TEXT,
                
                -- Who received it?
                payee TEXT,  -- e.g., "Marriott Hotel", artist name
                
                -- Bank reference (for reconciliation)
                bank_reference TEXT,
                
                -- Is this linked to a bank transaction?
                bank_id INTEGER,
                
                -- Notes
                notes TEXT,
                
                -- Timestamps
                created_at TEXT,
                created_by TEXT,
                
                FOREIGN KEY(show_id) REFERENCES shows(show_id),
                FOREIGN KEY(bank_id) REFERENCES bank_transactions(bank_id)
            )
        """)
        
        # =====================================================================
        # TABLE 7: HANDSHAKES (Bank ↔ Invoice Matches)
        # =====================================================================
        # A "handshake" links a bank payment to an invoice.
        # One bank payment can pay multiple invoices (one-to-many).
        # This is how we reconcile what we received vs what we billed.
        # =====================================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS handshakes (
                handshake_id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- The bank transaction being applied
                bank_id INTEGER NOT NULL,
                
                -- The invoice being paid
                invoice_id INTEGER NOT NULL,
                
                -- How much of the bank payment applies to this invoice?
                bank_amount_applied REAL NOT NULL,
                
                -- Proxy amount (adjustments for FX, fees, etc.)
                proxy_amount REAL DEFAULT 0,
                
                -- Notes explaining the match
                note TEXT,
                
                -- When was this match created?
                created_at TEXT,
                created_by TEXT,
                
                FOREIGN KEY(bank_id) REFERENCES bank_transactions(bank_id),
                FOREIGN KEY(invoice_id) REFERENCES invoices(invoice_id)
            )
        """)
        
        # =====================================================================
        # TABLE 8: SETTLEMENTS (Artist Payment Confirmation)
        # =====================================================================
        # Tracks the final settlement with artists.
        # Allows team to confirm when they've paid the artist.
        # =====================================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settlements (
                settlement_id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- Which show is this settlement for?
                show_id INTEGER NOT NULL,
                
                -- Artist being paid
                artist TEXT NOT NULL,
                
                -- What should be paid (calculated from show)
                amount_due REAL NOT NULL,
                currency TEXT DEFAULT 'GBP',
                
                -- What has been paid so far
                amount_paid REAL DEFAULT 0,
                
                -- Balance remaining
                balance REAL,
                
                -- Status
                status TEXT DEFAULT 'Pending',  -- Pending, Partial, Paid, Confirmed
                
                -- Payment details (when paid)
                payment_date TEXT,
                payment_reference TEXT,
                payment_method TEXT,  -- e.g., "Bank Transfer", "Wise"
                
                -- Confirmation
                confirmed_by TEXT,      -- Who confirmed the payment
                confirmed_at TEXT,      -- When was it confirmed
                artist_confirmed INTEGER DEFAULT 0,  -- Did artist confirm receipt?
                
                -- Notes
                notes TEXT,
                
                -- Timestamps
                created_at TEXT,
                updated_at TEXT,
                
                FOREIGN KEY(show_id) REFERENCES shows(show_id)
            )
        """)
        
        # =====================================================================
        # CREATE INDEXES
        # =====================================================================
        # Indexes make searches faster. Like an index in a book!
        # Without indexes, SQLite scans every row. With indexes, it jumps
        # directly to matching rows.
        #
        # Rule of thumb: Create indexes on columns you search/filter by.
        # =====================================================================
        
        # Shows indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_shows_contract ON shows(contract_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_shows_artist ON shows(artist)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_shows_agent ON shows(agent)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_shows_date ON shows(performance_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_shows_status ON shows(status)")
        
        # Contracts indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contracts_number ON contracts(contract_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contracts_artist ON contracts(artist)")
        
        # Bank transactions indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bank_date ON bank_transactions(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bank_hash ON bank_transactions(transaction_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bank_matched ON bank_transactions(is_matched)")
        
        # Invoices indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_number ON invoices(invoice_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_contract ON invoices(contract_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_show ON invoices(show_id)")
        
        # Invoice items index
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_invoice ON invoice_items(invoice_id)")
        
        # Outgoing payments indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_outgoing_show ON outgoing_payments(show_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_outgoing_type ON outgoing_payments(payment_type)")
        
        # Handshakes indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_handshakes_bank ON handshakes(bank_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_handshakes_invoice ON handshakes(invoice_id)")
        
        # Settlements indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_settlements_show ON settlements(show_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_settlements_status ON settlements(status)")
        
        # =====================================================================
        # COMMIT AND CLOSE
        # =====================================================================
        conn.commit()  # Save all changes
        conn.close()   # Release the connection
        
        print("[OK] Database initialized successfully!")
        print("   Tables created: shows, contracts, bank_transactions,")
        print("                   invoices, invoice_items, outgoing_payments,")
        print("                   handshakes, settlements")
        return True
        
    except Exception as e:
        print(f"[ERROR] Database initialization error: {e}")
        return False


def get_table_info():
    """
    Get information about all tables in the database.
    Useful for debugging and understanding the schema.
    
    RETURNS:
        dict: Table names mapped to their column information
    
    EXAMPLE OUTPUT:
        {
            'shows': [
                (0, 'show_id', 'INTEGER', 0, None, 1),
                (1, 'contract_number', 'TEXT', 0, None, 0),
                ...
            ],
            'invoices': [...],
            ...
        }
    
    WHAT THE COLUMN INFO MEANS:
        (cid, name, type, notnull, default_value, pk)
        - cid: Column index (0, 1, 2...)
        - name: Column name
        - type: Data type (INTEGER, TEXT, REAL)
        - notnull: 1 if NOT NULL constraint, 0 otherwise
        - default_value: Default value if any
        - pk: 1 if primary key, 0 otherwise
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get list of all tables
        # sqlite_master is a special table that lists all objects in the database
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        # Get column info for each table
        table_info = {}
        for table in tables:
            # PRAGMA table_info returns column details
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            table_info[table] = columns
        
        conn.close()
        return table_info
        
    except Exception as e:
        print(f"[ERROR] Error getting table info: {e}")
        return {}


# =============================================================================
# LEARNING NOTES: SQL DATA TYPES
# =============================================================================
#
# INTEGER: Whole numbers (1, 2, 3, -5, 0)
#          Used for: IDs, counts, yes/no flags (0/1)
#
# REAL:    Decimal numbers (3.14, 100.50, -0.001)
#          Used for: Money amounts, percentages
#
# TEXT:    Strings/text of any length
#          Used for: Names, descriptions, dates (stored as strings)
#
# BLOB:    Binary data (images, files)
#          We don't use this in our app
#
# NULL:    "No value" / "Unknown"
#          Different from 0 or empty string!
#
# =============================================================================
# LEARNING NOTES: CONSTRAINTS
# =============================================================================
#
# PRIMARY KEY: Unique identifier for each row. Can't be NULL or duplicate.
#
# NOT NULL: Column must have a value. Can't be empty.
#
# UNIQUE: No two rows can have the same value in this column.
#
# DEFAULT: Value to use if none provided when inserting.
#
# FOREIGN KEY: References a column in another table.
#              Ensures data integrity (can't reference non-existent records).
#
# =============================================================================

