# =============================================================================
# importers/invoice_importer.py
# =============================================================================
# PURPOSE:
#   Imports invoice CSV files with line items.
#   Handles the "long format" where each row is a line item,
#   and multiple rows share the same invoice number.
#
# INVOICE FORMAT (Long Format):
#   InvoiceNumber | Contract Number | From Entity | AccountCode | Net | VAT | Gross | Currency
#   ARC/I25-001   | 910516          | Arcade Ltd  | Booking Fee | 500 | 0   | 500   | GBP
#   ARC/I25-001   | 910516          | Arcade Ltd  | Artist Fee  | 2000| 0   | 2000  | GBP
#   ARC/I25-002   | 910517          | Arcade Ltd  | Booking Fee | 800 | 160 | 960   | GBP
#
#   In this example:
#   - Invoice ARC/I25-001 has 2 line items (Booking Fee + Artist Fee)
#   - Invoice ARC/I25-002 has 1 line item (Booking Fee with VAT)
#
# WHAT THIS IMPORTER DOES:
#   1. Groups rows by invoice number
#   2. For each invoice:
#      a. Creates the INVOICE header record
#      b. Creates INVOICE_ITEMS for each line item
#      c. Calculates totals (sum of line items)
#   3. Detects duplicates by invoice number
#   4. Optionally links to shows via contract number
#
# DUPLICATE DETECTION:
#   Invoice numbers must be unique. If an invoice number already exists,
#   we skip it and report it as a duplicate.
# =============================================================================

import pandas as pd
from datetime import datetime
from database import (
    get_db_connection,
    create_invoice,
    check_invoice_exists,
    load_shows
)


class InvoiceImporter:
    """
    Imports invoice CSV files with line items.
    
    USAGE:
        importer = InvoiceImporter("invoices.csv")
        success, message, count = importer.import_invoices()
    
    FEATURES:
        - Handles "long format" CSVs (multiple rows per invoice)
        - Auto-calculates invoice totals from line items
        - Duplicate detection by invoice number
        - Links invoices to shows via contract number
        - Flexible column detection
    """
    
    def __init__(self, source):
        """
        Initialize the invoice importer.
        
        PARAMETERS:
            source: File path or file-like object
        """
        self.source = source
        self.batch_id = datetime.now().strftime("batch_%Y%m%d_%H%M%S")
        self.errors = []
        self.skipped = []
        self.duplicates = []
    
    def import_invoices(self):
        """
        Main method: Import invoices from the file.
        
        RETURNS:
            tuple: (success, message, count)
        
        PROCESS:
            1. Read CSV
            2. Group rows by invoice number
            3. For each group, create invoice + line items
            4. Link to shows where possible
        """
        try:
            # Read CSV
            df = pd.read_csv(self.source)
            
            print(f"[INFO] Read CSV with {len(df)} rows")
            print(f"   Columns: {list(df.columns)}")
            
            # Group rows by invoice number
            grouped_invoices = self._group_by_invoice(df)
            
            if self.errors:
                return False, "\n".join(self.errors), 0
            
            if not grouped_invoices:
                return False, "No valid invoices found in CSV", 0
            
            # Insert invoices
            invoice_count, item_count = self._insert_invoices(grouped_invoices)
            
            # Build result message
            msg_parts = [f"Imported {invoice_count} invoices with {item_count} line items"]
            if self.duplicates:
                msg_parts.append(f"{len(self.duplicates)} duplicates skipped")
            if self.skipped:
                msg_parts.append(f"{len(self.skipped)} rows skipped")
            
            return True, " | ".join(msg_parts), invoice_count
            
        except Exception as e:
            return False, f"Import error: {str(e)}", 0
    
    def _group_by_invoice(self, df):
        """
        Group CSV rows by invoice number.
        
        WHAT THIS DOES:
            Takes a "long format" CSV where each row is a line item,
            and groups them into invoices.
        
        EXAMPLE INPUT (DataFrame):
            InvoiceNumber | AccountCode | Gross
            INV-001       | Booking Fee | 500
            INV-001       | Artist Fee  | 2000
            INV-002       | Booking Fee | 800
        
        EXAMPLE OUTPUT (List of dicts):
            [
                {
                    'invoice_number': 'INV-001',
                    'total_gross': 2500,
                    'line_items': [
                        {'account_code': 'Booking Fee', 'gross': 500},
                        {'account_code': 'Artist Fee', 'gross': 2000}
                    ]
                },
                {
                    'invoice_number': 'INV-002',
                    'total_gross': 800,
                    'line_items': [
                        {'account_code': 'Booking Fee', 'gross': 800}
                    ]
                }
            ]
        
        RETURNS:
            list: List of invoice dictionaries
        """
        # Detect columns
        col_map = self._detect_columns(df)
        
        # Validate required columns
        if not col_map.get('invoice_number'):
            self.errors.append("Missing required column: Invoice Number")
            return []
        
        # Determine format: Simple (has 'value' column) or Long (has 'account_code' + 'gross')
        # Simple format: one row per invoice with a single Value column
        # Long format: multiple rows per invoice with AccountCode and Gross columns
        is_simple_format = col_map.get('value') and not col_map.get('account_code')
        
        if not is_simple_format:
            # Long format requires account_code and gross
            if not col_map.get('account_code'):
                self.errors.append("Missing required column: Account Code (for long format)")
                return []
            if not col_map.get('gross'):
                self.errors.append("Missing required column: Gross Amount (for long format)")
                return []
        
        print(f"[INFO] Detected format: {'Simple (one row per invoice)' if is_simple_format else 'Long (multiple rows per invoice)'}")
        
        # Dictionary to hold invoices as we build them
        # Key = invoice number, Value = invoice dict
        invoices = {}
        
        # Process each row
        for idx, row in df.iterrows():
            row_num = idx + 2
            
            # Get invoice number
            inv_num = self._get_value(row, col_map.get('invoice_number'))
            if not inv_num:
                self.skipped.append(f"Row {row_num}: No invoice number")
                continue
            
            # =====================================================================
            # SIMPLE FORMAT: One row per invoice with a single Value column
            # =====================================================================
            if is_simple_format:
                # Get the value
                value = self._get_float(row, col_map.get('value'))
                if not value:
                    self.skipped.append(f"Row {row_num}: No value")
                    continue
                
                # Get description (used as both reference and line item description)
                description = self._get_value(row, col_map.get('description'))
                
                # Create invoice with single line item
                invoices[inv_num] = {
                    'invoice_number': inv_num,
                    'contract_number': self._get_value(row, col_map.get('contract_number')),
                    'from_entity': self._get_value(row, col_map.get('from_entity')),
                    'promoter_name': self._get_value(row, col_map.get('promoter_name')),
                    'payment_bank_details': self._get_value(row, col_map.get('payment_bank_details')),
                    'reference': description,  # Use description as reference
                    'currency': self._get_value(row, col_map.get('currency'), default='GBP').upper(),
                    'invoice_date': self._get_value(row, col_map.get('invoice_date')),
                    'show_date': self._get_value(row, col_map.get('show_date')),
                    'line_items': [{
                        'account_code': 'Invoice Total',  # Default account code for simple format
                        'description': description,
                        'net': value,
                        'vat': 0.0,
                        'gross': value
                    }]
                }
                continue
            
            # =====================================================================
            # LONG FORMAT: Multiple rows per invoice with AccountCode and Gross
            # =====================================================================
            # Get account code (required for line items in long format)
            account_code = self._get_value(row, col_map.get('account_code'))
            if not account_code:
                self.skipped.append(f"Row {row_num}: No account code")
                continue
            
            # If this is the first time we see this invoice, initialize it
            if inv_num not in invoices:
                invoices[inv_num] = {
                    'invoice_number': inv_num,
                    'contract_number': self._get_value(row, col_map.get('contract_number')),
                    'from_entity': self._get_value(row, col_map.get('from_entity')),
                    'promoter_name': self._get_value(row, col_map.get('promoter_name')),
                    'payment_bank_details': self._get_value(row, col_map.get('payment_bank_details')),
                    'reference': self._get_value(row, col_map.get('reference')),
                    'currency': self._get_value(row, col_map.get('currency'), default='GBP').upper(),
                    'invoice_date': self._get_value(row, col_map.get('invoice_date')),
                    'show_date': self._get_value(row, col_map.get('show_date')),
                    'line_items': []
                }
            
            # Parse line item amounts
            gross = self._get_float(row, col_map.get('gross'))
            net = self._get_float(row, col_map.get('net'))
            vat = self._get_float(row, col_map.get('vat'))
            
            # Add line item to invoice
            invoices[inv_num]['line_items'].append({
                'account_code': account_code,
                'description': self._get_value(row, col_map.get('description')),
                'net': net,
                'vat': vat,
                'gross': gross
            })
        
        # Calculate totals for each invoice
        invoice_list = []
        for inv_num, invoice in invoices.items():
            # Skip invoices with no line items
            if not invoice['line_items']:
                continue
            
            # Sum up line items
            invoice['total_gross'] = sum(item['gross'] for item in invoice['line_items'])
            invoice['total_net'] = sum(item['net'] for item in invoice['line_items'] if item['net'])
            invoice['total_vat'] = sum(item['vat'] for item in invoice['line_items'] if item['vat'])
            
            invoice_list.append(invoice)
        
        print(f"[INFO] Grouped {len(df)} rows into {len(invoice_list)} invoices")
        
        return invoice_list
    
    def _detect_columns(self, df):
        """
        Detect which columns contain which data.
        
        SUPPORTS TWO FORMATS:
        
        FORMAT 1 - Simple (one row per invoice):
            Invoice Number | Contract Number | Invoice Date | Description | Value | Currency
            INV-2026-001   | 900100          | 2026-03-01   | Deposit     | 1000  | GBP
        
        FORMAT 2 - Long (multiple rows per invoice with line items):
            Invoice Number | Contract Number | AccountCode  | Net  | VAT | Gross | Currency
            INV-001        | 900100          | Booking Fee  | 500  | 0   | 500   | GBP
            INV-001        | 900100          | Artist Fee   | 2000 | 0   | 2000  | GBP
        
        RETURNS:
            dict: Mapping of our field names to actual column names
        """
        column_mappings = {
            # Invoice identification
            'invoice_number': ['invoice number', 'invoice', 'inv', 'invoicenumber'],
            'contract_number': ['contract number', 'contract', 'booking id'],
            
            # Entity info
            'from_entity': ['from entity', 'from', 'sender', 'company'],
            'promoter_name': ['contact', 'promoter', 'client', 'contact name', 'customer'],
            'payment_bank_details': ['payment bank details', 'pay to', 'bank details'],
            
            # Reference/description
            'reference': ['reference', 'event', 'ref'],
            'description': ['description', 'line description', 'item description'],
            
            # Currency
            'currency': ['currency', 'ccy', 'curr'],
            
            # Line item details (for long format)
            'account_code': ['accountcode', 'account code', 'item type', 'account_code', 'type'],
            'net': ['net amount', 'net', 'nett'],
            'vat': ['vat amount', 'vat', 'tax'],
            'gross': ['gross amount', 'gross', 'total', 'amount'],
            
            # Simple format - single value column
            'value': ['value', 'amount', 'total'],
            
            # Dates
            'invoice_date': ['invoice date', 'date', 'inv date'],
            'show_date': ['show date', 'event date', 'performance date'],
        }
        
        col_map = {}
        
        for field, possible_names in column_mappings.items():
            for col in df.columns:
                col_lower = col.lower().strip()
                for name in possible_names:
                    if name.lower() in col_lower:
                        col_map[field] = col
                        break
                if field in col_map:
                    break
        
        print(f"[INFO] Column mapping:")
        for field, col in col_map.items():
            print(f"   {field} -> {col}")
        
        return col_map
    
    def _get_value(self, row, col_name, default=None):
        """Safely get a string value from a row."""
        if not col_name or col_name not in row.index:
            return default
        
        value = row[col_name]
        
        if pd.isna(value):
            return default
        
        str_val = str(value).strip()
        if not str_val or str_val.lower() in ('nan', 'none'):
            return default
        
        return str_val
    
    def _get_float(self, row, col_name, default=0.0):
        """Safely get a float value from a row."""
        value = self._get_value(row, col_name)
        if value is None:
            return default
        
        try:
            cleaned = value.replace(',', '').replace('£', '').replace('$', '').replace('€', '')
            return float(cleaned)
        except:
            return default
    
    def _insert_invoices(self, invoices):
        """
        Insert invoices and their line items to the database.
        
        PARAMETERS:
            invoices: List of invoice dictionaries from _group_by_invoice
        
        RETURNS:
            tuple: (invoice_count, item_count)
        """
        invoice_count = 0
        item_count = 0
        
        for invoice in invoices:
            inv_num = invoice['invoice_number']
            
            # Check for duplicate
            if check_invoice_exists(inv_num):
                self.duplicates.append(inv_num)
                continue
            
            # Try to find the show this invoice belongs to
            show_id = self._find_show_for_invoice(invoice)
            
            # Prepare invoice data (without line_items)
            invoice_data = {k: v for k, v in invoice.items() if k != 'line_items'}
            invoice_data['import_batch'] = self.batch_id
            if show_id:
                invoice_data['show_id'] = show_id
            
            # Create invoice with line items
            invoice_id = create_invoice(invoice_data, invoice['line_items'])
            
            if invoice_id:
                invoice_count += 1
                item_count += len(invoice['line_items'])
        
        return invoice_count, item_count
    
    def _find_show_for_invoice(self, invoice):
        """
        Try to find the show this invoice belongs to.
        
        MATCHING LOGIC:
            Invoices attach to shows via contract_number. The contract number
            in the invoice CSV must match the contract_number on a show
            (shows get contract_number when contracts are imported).
            We normalize by stripping whitespace so "910516" and " 910516 "
            match.
        
        RETURNS:
            int or None: show_id if found, None otherwise
        """
        raw = invoice.get('contract_number')
        if not raw:
            return None
        contract_num = str(raw).strip()
        if not contract_num:
            return None
        # Match show by contract_number (set when contracts are imported)
        shows_df = load_shows(filters={'contract_number': contract_num})
        if len(shows_df) > 0:
            return int(shows_df.iloc[0]['show_id'])
        return None
    
    def get_import_summary(self):
        """Get detailed import summary."""
        return {
            'batch_id': self.batch_id,
            'errors': self.errors,
            'skipped': self.skipped,
            'duplicates': self.duplicates,
        }


# =============================================================================
# LEARNING NOTES: GROUPING DATA
# =============================================================================
#
# WHY GROUP DATA?
#   Sometimes data comes in a "flat" format where related items are
#   spread across multiple rows. We need to group them together.
#
# EXAMPLE: Invoice with line items
#   
#   FLAT FORMAT (how it comes in CSV):
#   | Invoice | Item        | Amount |
#   | INV-001 | Booking Fee | 500    |
#   | INV-001 | Artist Fee  | 2000   |
#   | INV-002 | Booking Fee | 800    |
#   
#   GROUPED FORMAT (what we want):
#   Invoice INV-001:
#     - Booking Fee: 500
#     - Artist Fee: 2000
#     - Total: 2500
#   
#   Invoice INV-002:
#     - Booking Fee: 800
#     - Total: 800
#
# HOW WE GROUP:
#   1. Create a dictionary with invoice number as key
#   2. Loop through rows
#   3. For each row, add to the appropriate invoice
#   4. At the end, calculate totals
#
# ALTERNATIVE: pandas groupby
#   df.groupby('InvoiceNumber').apply(process_group)
#   
#   This is more "Pythonic" but harder to understand for beginners.
#   Our manual approach is clearer for learning.
#
# =============================================================================

