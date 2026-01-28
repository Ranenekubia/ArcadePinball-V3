# =============================================================================
# importers/bank_importer.py
# =============================================================================
# PURPOSE:
#   Imports HSBC bank statement CSV files into the database.
#   
# HSBC BANK STATEMENT FORMAT:
#   Date,Type,Description,Paid Out,Paid In,Currency
#   2025-07-18,CR,F&B OPERATING ACC ATA INV-16496,,9800,GBP
#   2025-10-03,,St Martins Place,800,,GBP
#
# WHAT THIS IMPORTER DOES:
#   1. Reads the CSV file
#   2. Detects columns (handles different column names)
#   3. Parses each row:
#      - Extracts date, description, amounts
#      - Calculates net amount (paid_in - paid_out)
#      - Validates currency
#   4. Checks for duplicates using a hash
#   5. Inserts new transactions to database
#   6. Reports success/failures
#
# DUPLICATE DETECTION:
#   We create a hash of: date + amount + description
#   If a transaction with the same hash exists, we skip it.
#   This prevents importing the same statement twice.
# =============================================================================

import pandas as pd
from datetime import datetime
import hashlib
from database import get_db_connection, create_bank_transaction, check_bank_transaction_exists


class BankImporter:
    """
    Imports HSBC bank statement CSV files.
    
    USAGE:
        # From a file path
        importer = BankImporter("bank_statement.csv")
        success, message, count = importer.import_transactions()
        
        # From a Streamlit uploaded file
        importer = BankImporter(uploaded_file)
        success, message, count = importer.import_transactions()
    
    ATTRIBUTES:
        source: The file path or file object to import
        batch_id: Unique identifier for this import batch
        errors: List of error messages encountered
        skipped: List of skipped rows (with reasons)
        duplicates: List of duplicate transactions found
    """
    
    def __init__(self, source):
        """
        Initialize the bank importer.
        
        PARAMETERS:
            source: Either a file path (string) or a file-like object
                   (e.g., Streamlit's UploadedFile)
        
        WHAT HAPPENS:
            1. Store the source
            2. Generate a unique batch ID (for tracking this import)
            3. Initialize empty lists for errors/skipped/duplicates
        """
        self.source = source
        
        # Generate a unique batch ID
        # Format: "batch_YYYYMMDD_HHMMSS"
        # This helps us track which transactions came from which import
        self.batch_id = datetime.now().strftime("batch_%Y%m%d_%H%M%S")
        
        # Lists to track problems during import
        self.errors = []      # Serious problems (couldn't parse row)
        self.skipped = []     # Rows we intentionally skipped (empty, zero amount)
        self.duplicates = []  # Rows that already exist in database
    
    def import_transactions(self):
        """
        Main method: Parse the CSV and import transactions.
        
        RETURNS:
            tuple: (success: bool, message: str, count: int)
            - success: True if at least some rows imported
            - message: Human-readable result message
            - count: Number of rows successfully imported
        
        PROCESS:
            1. Read CSV into pandas DataFrame
            2. Parse each row into structured data
            3. Check for duplicates
            4. Insert non-duplicates to database
            5. Build result message
        """
        try:
            # -----------------------------------------------------------------
            # STEP 1: Read the CSV file
            # -----------------------------------------------------------------
            # pandas.read_csv() can handle both file paths and file objects
            df = pd.read_csv(self.source)
            
            print(f"[INFO] Read CSV with {len(df)} rows")
            print(f"   Columns found: {list(df.columns)}")
            
            # -----------------------------------------------------------------
            # STEP 2: Parse rows into structured data
            # -----------------------------------------------------------------
            rows_to_insert = self._parse_rows(df)
            
            # -----------------------------------------------------------------
            # STEP 3: Build result message
            # -----------------------------------------------------------------
            message_parts = []
            
            # Report errors
            if self.errors:
                message_parts.append(f"{len(self.errors)} errors")
            
            # Report skipped
            if self.skipped:
                message_parts.append(f"{len(self.skipped)} skipped")
            
            # Report duplicates
            if self.duplicates:
                message_parts.append(f"{len(self.duplicates)} duplicates")
            
            # Check if we have anything to import
            if not rows_to_insert:
                if message_parts:
                    return False, "No new transactions. " + ", ".join(message_parts), 0
                return False, "No valid transactions found in CSV", 0
            
            # -----------------------------------------------------------------
            # STEP 4: Insert to database
            # -----------------------------------------------------------------
            count = self._insert_to_database(rows_to_insert)
            
            # Build success message
            success_msg = f"Imported {count} transactions"
            if message_parts:
                success_msg += " (" + ", ".join(message_parts) + ")"
            
            return True, success_msg, count
            
        except Exception as e:
            # Something went wrong at a high level
            return False, f"Import error: {str(e)}", 0
    
    def _parse_rows(self, df):
        """
        Parse CSV rows into structured transaction data.
        
        PARAMETERS:
            df (pd.DataFrame): Raw CSV data
        
        RETURNS:
            list: List of dictionaries, each representing a valid transaction
        
        WHAT THIS DOES:
            1. Detect which columns contain date, description, amounts, etc.
            2. Loop through each row
            3. Extract and validate data
            4. Check for duplicates
            5. Return list of valid transactions
        """
        rows_to_insert = []
        
        # -----------------------------------------------------------------
        # DETECT COLUMNS
        # -----------------------------------------------------------------
        # Different bank exports might have different column names.
        # We try to find the right column by checking common names.
        
        date_col = self._find_column(df, ['date', 'transaction date', 'txn date'])
        desc_col = self._find_column(df, ['description', 'narrative', 'details', 'reference'])
        type_col = self._find_column(df, ['type', 'transaction type', 'txn type'])
        credit_col = self._find_column(df, ['paid in', 'credit', 'cr', 'amount in'])
        debit_col = self._find_column(df, ['paid out', 'debit', 'dr', 'amount out'])
        currency_col = self._find_column(df, ['currency', 'ccy', 'curr'])
        
        # Validate required columns
        if not date_col:
            self.errors.append("Missing required column: Date")
            return []
        if not desc_col:
            self.errors.append("Missing required column: Description")
            return []
        
        # Debug output
        print(f"[INFO] Column mapping:")
        print(f"   Date: {date_col}")
        print(f"   Description: {desc_col}")
        print(f"   Type: {type_col}")
        print(f"   Credit (Paid In): {credit_col}")
        print(f"   Debit (Paid Out): {debit_col}")
        print(f"   Currency: {currency_col}")
        
        # -----------------------------------------------------------------
        # PROCESS EACH ROW
        # -----------------------------------------------------------------
        for idx, row in df.iterrows():
            # Row number for error messages (add 2: 1 for header, 1 for 0-indexing)
            row_num = idx + 2
            
            # --- Parse Date ---
            date_val = self._get_cell_value(row, date_col)
            if not date_val:
                self.skipped.append(f"Row {row_num}: Empty date")
                continue
            
            # --- Parse Description ---
            desc_val = self._get_cell_value(row, desc_col)
            if not desc_val:
                self.skipped.append(f"Row {row_num}: Empty description")
                continue
            
            # --- Parse Type (optional) ---
            type_val = self._get_cell_value(row, type_col) if type_col else None
            
            # --- Parse Amounts ---
            # Credit = money coming IN (positive)
            # Debit = money going OUT (negative)
            credit = self._parse_amount(row, credit_col) if credit_col else 0.0
            debit = self._parse_amount(row, debit_col) if debit_col else 0.0
            
            # Calculate net amount
            # Positive = money received, Negative = money paid out
            amount = credit - debit
            
            # Skip zero amounts
            if abs(amount) < 0.01:
                self.skipped.append(f"Row {row_num}: Zero amount")
                continue
            
            # --- Parse Currency ---
            currency = "GBP"  # Default
            if currency_col:
                curr_val = self._get_cell_value(row, currency_col)
                if curr_val and curr_val.upper() in ['GBP', 'EUR', 'USD', 'AUD']:
                    currency = curr_val.upper()
            
            # --- Check for Duplicate ---
            if check_bank_transaction_exists(date_val, amount, desc_val):
                self.duplicates.append(f"Row {row_num}: {desc_val[:30]}...")
                continue
            
            # --- Add to insert list ---
            rows_to_insert.append({
                'date': date_val,
                'type': type_val,
                'description': desc_val,
                'paid_out': debit,
                'paid_in': credit,
                'amount': amount,
                'currency': currency,
                'import_batch': self.batch_id
            })
        
        print(f"\n[INFO] Parse Summary:")
        print(f"   Total rows: {len(df)}")
        print(f"   Valid: {len(rows_to_insert)}")
        print(f"   Duplicates: {len(self.duplicates)}")
        print(f"   Skipped: {len(self.skipped)}")
        print(f"   Errors: {len(self.errors)}")
        
        return rows_to_insert
    
    def _find_column(self, df, possible_names):
        """
        Find a column by matching against possible names.
        
        PARAMETERS:
            df: DataFrame to search
            possible_names: List of possible column names (lowercase)
        
        RETURNS:
            str or None: The actual column name if found, None otherwise
        
        HOW IT WORKS:
            We check each column name against our list of possible names.
            First we try exact matches, then partial matches.
            Matching is case-insensitive.
            
            Example: Column "Paid In" exactly matches "paid in"
                     Column "Transaction Date" partially matches "date"
        """
        # First pass: exact matches (more reliable)
        for col in df.columns:
            col_lower = col.lower().strip()
            for name in possible_names:
                if col_lower == name.lower():
                    return col
        
        # Second pass: partial matches (column contains the name)
        for col in df.columns:
            col_lower = col.lower().strip()
            for name in possible_names:
                # Only match if the name is a significant part of the column name
                # Avoid matching "in" in "Description"
                if name.lower() in col_lower and len(name) > 2:
                    return col
        
        return None
    
    def _get_cell_value(self, row, col_name):
        """
        Safely get a cell value from a row.
        
        PARAMETERS:
            row: pandas Series (one row of data)
            col_name: Column name to get
        
        RETURNS:
            str or None: The cell value as a string, or None if empty
        
        WHY THIS EXISTS:
            Cell values can be:
            - Normal values: "Hello"
            - NaN (Not a Number): pandas uses this for empty cells
            - None
            - Whitespace only: "   "
            
            This function handles all cases and returns a clean string or None.
        """
        if not col_name or col_name not in row:
            return None
        
        value = row[col_name]
        
        # Check for NaN (pandas empty cell marker)
        if pd.isna(value):
            return None
        
        # Convert to string and strip whitespace
        str_value = str(value).strip()
        
        # Check for empty or "nan" string
        if not str_value or str_value.lower() == 'nan':
            return None
        
        return str_value
    
    def _parse_amount(self, row, col_name):
        """
        Parse a monetary amount from a cell.
        
        PARAMETERS:
            row: pandas Series
            col_name: Column name containing the amount
        
        RETURNS:
            float: The amount, or 0.0 if parsing fails
        
        HANDLES:
            - Empty cells → 0.0
            - Commas in numbers: "1,000.00" → 1000.00
            - Currency symbols: "$100" → 100.0
            - Negative signs: "-50" → -50.0
        """
        value = self._get_cell_value(row, col_name)
        if not value:
            return 0.0
        
        try:
            # Remove commas and currency symbols
            cleaned = value.replace(',', '').replace('£', '').replace('$', '').replace('€', '').strip()
            return float(cleaned)
        except (ValueError, TypeError):
            return 0.0
    
    def _insert_to_database(self, rows):
        """
        Insert parsed rows into the database.
        
        PARAMETERS:
            rows: List of transaction dictionaries
        
        RETURNS:
            int: Number of rows successfully inserted
        """
        inserted_count = 0
        
        for row in rows:
            # create_bank_transaction handles the actual INSERT
            # It returns the new bank_id, or None if failed
            result = create_bank_transaction(row)
            if result:
                inserted_count += 1
        
        return inserted_count
    
    def get_import_summary(self):
        """
        Get a detailed summary of the import.
        
        RETURNS:
            dict: Summary with errors, skipped, and duplicates lists
        """
        return {
            'batch_id': self.batch_id,
            'errors': self.errors,
            'skipped': self.skipped,
            'duplicates': self.duplicates,
            'error_count': len(self.errors),
            'skipped_count': len(self.skipped),
            'duplicate_count': len(self.duplicates)
        }


# =============================================================================
# LEARNING NOTES: PANDAS BASICS
# =============================================================================
#
# WHAT IS PANDAS?
#   Pandas is a Python library for data manipulation.
#   It's like Excel in Python!
#
# KEY CONCEPTS:
#
# DataFrame: A 2D table (like an Excel sheet)
#   df = pd.read_csv("file.csv")
#   df.columns  → List of column names
#   df.head()   → First 5 rows
#   len(df)     → Number of rows
#
# Series: A single column (like one column in Excel)
#   row = df.iloc[0]  → First row as a Series
#   row['column']     → Value in that column
#
# Iteration:
#   for idx, row in df.iterrows():
#       print(row['column'])
#
# Checking for empty:
#   pd.isna(value)  → True if value is NaN/None
#   pd.notna(value) → True if value has data
#
# =============================================================================

