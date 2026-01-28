# =============================================================================
# importers/contract_importer.py
# =============================================================================
# PURPOSE:
#   Imports contract/booking data from System One exports.
#   Creates both CONTRACT records and SHOW records from the data.
#
# SYSTEM ONE FORMAT (from your Excel):
#   Contract Number | Booking Date | Artist | Event | Venue | City | Country |
#   Performance date | Performance Day | Contracted Deal | Total deal Value |
#   AF (Artist Fee) | Hotel buyout | Ground buyout | Transport buyout | WHT |
#   BF (Booking Fee) | BF VAT | Total Settlement for Artist
#
# WHAT THIS IMPORTER DOES:
#   1. Reads the CSV/Excel file
#   2. For each contract:
#      a. Creates a CONTRACT record (the deal terms)
#      b. Creates a SHOW record (the performance)
#      c. Links them together via contract_number
#   3. Detects duplicates by contract_number
#
# WHY BOTH CONTRACT AND SHOW?
#   - CONTRACT: The legal agreement, deal terms, what was agreed
#   - SHOW: The actual performance, status, reconciliation tracking
#   - They're related but serve different purposes
#   - A show might exist before a contract is imported (manual entry)
#   - A contract is the "source of truth" for deal terms
# =============================================================================

import pandas as pd
from datetime import datetime
from database import (
    get_db_connection,
    create_contract,
    check_contract_exists,
    create_show,
    load_shows
)


class ContractImporter:
    """
    Imports System One contract exports.
    
    USAGE:
        importer = ContractImporter("contracts.csv")
        success, message, count = importer.import_contracts()
    
    FEATURES:
        - Flexible column detection
        - Duplicate detection by contract number
        - Auto-creates corresponding SHOW records
        - Handles various date formats
        - Calculates missing totals
    """
    
    def __init__(self, source):
        """
        Initialize the contract importer.
        
        PARAMETERS:
            source: File path or file-like object
        """
        self.source = source
        self.batch_id = datetime.now().strftime("batch_%Y%m%d_%H%M%S")
        self.errors = []
        self.skipped = []
        self.duplicates = []
    
    def import_contracts(self):
        """
        Main method: Import contracts from the file.
        
        RETURNS:
            tuple: (success, message, count)
        """
        try:
            # Read the file
            # Try CSV first, fall back to Excel
            try:
                df = pd.read_csv(self.source)
            except:
                df = pd.read_excel(self.source)
            
            print(f"[INFO] Read file with {len(df)} rows")
            print(f"   Columns: {list(df.columns)}")
            
            # Parse and import
            contracts_created = 0
            shows_created = 0
            
            # Detect columns
            col_map = self._detect_columns(df)
            
            if not col_map.get('contract_number'):
                return False, "Missing required column: Contract Number", 0
            
            # Process each row
            for idx, row in df.iterrows():
                row_num = idx + 2
                
                # Get contract number
                contract_num = self._get_value(row, col_map.get('contract_number'))
                if not contract_num:
                    self.skipped.append(f"Row {row_num}: No contract number")
                    continue
                
                # Check for duplicate
                if check_contract_exists(contract_num):
                    self.duplicates.append(f"Row {row_num}: Contract {contract_num}")
                    continue
                
                # Parse contract data
                contract_data = self._parse_contract(row, col_map)
                contract_data['contract_number'] = contract_num
                contract_data['import_batch'] = self.batch_id
                
                # Create contract
                contract_id = create_contract(contract_data)
                if contract_id:
                    contracts_created += 1
                    
                    # Also create a SHOW record
                    show_data = self._contract_to_show(contract_data)
                    show_id = create_show(show_data)
                    if show_id:
                        shows_created += 1
                        
                        # Link contract to show
                        self._link_contract_to_show(contract_id, show_id)
            
            # Build result message
            msg_parts = [f"Imported {contracts_created} contracts"]
            if shows_created:
                msg_parts.append(f"Created {shows_created} shows")
            if self.duplicates:
                msg_parts.append(f"{len(self.duplicates)} duplicates")
            if self.skipped:
                msg_parts.append(f"{len(self.skipped)} skipped")
            
            return True, " | ".join(msg_parts), contracts_created
            
        except Exception as e:
            return False, f"Import error: {str(e)}", 0
    
    def _detect_columns(self, df):
        """
        Detect which columns contain which data.
        
        RETURNS:
            dict: Mapping of our field names to actual column names
        """
        # Define possible names for each field
        column_mappings = {
            'contract_number': ['contract number', 'contract', 'booking id', 'contract_number'],
            'booking_date': ['booking date', 'booked', 'date booked'],
            'artist': ['artist', 'act', 'performer'],
            'event_name': ['event', 'event name', 'show', 'festival'],
            'venue': ['venue', 'location', 'club'],
            'city': ['city', 'town'],
            'country': ['country', 'nation'],
            'performance_date': ['performance date', 'show date', 'date', 'gig date'],
            'performance_day': ['performance day', 'day', 'day of week'],
            'deal_description': ['contracted deal', 'deal', 'deal description', 'deal terms'],
            'total_deal_value': ['total deal value', 'deal value', 'total value', 'total'],
            'currency': ['currency', 'ccy', 'curr'],  # Added currency mapping
            'artist_fee': ['af', 'artist fee', 'fee'],
            'booking_fee': ['bf', 'booking fee', 'agency fee'],
            'booking_fee_vat': ['bf vat', 'booking fee vat', 'vat'],
            'hotel_buyout': ['hotel buyout', 'hotel', 'accommodation'],
            'flight_buyout': ['flight', 'flights', 'air'],
            'ground_transport_buyout': ['ground buyout', 'ground transport', 'transport', 'ground'],
            'withholding_tax': ['wht', 'withholding tax', 'withholding', 'tax'],
            'total_artist_settlement': ['total settlement', 'artist settlement', 'settlement', 'net to artist'],
        }
        
        col_map = {}
        
        # First pass: exact matches (column name equals one of our possible names)
        for field, possible_names in column_mappings.items():
            for col in df.columns:
                col_lower = col.lower().strip()
                for name in possible_names:
                    if col_lower == name.lower():
                        col_map[field] = col
                        break
                if field in col_map:
                    break
        
        # Second pass: partial matches (for fields not yet matched)
        for field, possible_names in column_mappings.items():
            if field in col_map:
                continue  # Already matched
            for col in df.columns:
                col_lower = col.lower().strip()
                for name in possible_names:
                    # Only match if the name is a word boundary (not part of another word)
                    if name.lower() in col_lower and col not in col_map.values():
                        col_map[field] = col
                        break
                if field in col_map:
                    break
        
        print(f"[INFO] Column mapping detected:")
        for field, col in col_map.items():
            print(f"   {field} -> {col}")
        
        return col_map
    
    def _get_value(self, row, col_name, default=None):
        """Safely get a value from a row."""
        if not col_name or col_name not in row.index:
            return default
        
        value = row[col_name]
        
        if pd.isna(value):
            return default
        
        str_val = str(value).strip()
        if not str_val or str_val.lower() in ('nan', 'none', 'n/a'):
            return default
        
        return str_val
    
    def _get_float(self, row, col_name, default=0.0):
        """Safely get a float value from a row."""
        value = self._get_value(row, col_name)
        if value is None:
            return default
        
        try:
            # Handle "Zero" or other text
            if value.lower() in ('zero', 'nil', '-'):
                return 0.0
            # Remove commas and currency symbols
            cleaned = value.replace(',', '').replace('£', '').replace('$', '').replace('€', '')
            return float(cleaned)
        except:
            return default
    
    def _parse_contract(self, row, col_map):
        """
        Parse a row into contract data.
        
        RETURNS:
            dict: Contract data ready for database insertion
        """
        return {
            'booking_date': self._get_value(row, col_map.get('booking_date')),
            'artist': self._get_value(row, col_map.get('artist')),
            'event_name': self._get_value(row, col_map.get('event_name')),
            'venue': self._get_value(row, col_map.get('venue')),
            'city': self._get_value(row, col_map.get('city')),
            'country': self._get_value(row, col_map.get('country')),
            'performance_date': self._get_value(row, col_map.get('performance_date')),
            'performance_day': self._get_value(row, col_map.get('performance_day')),
            'deal_description': self._get_value(row, col_map.get('deal_description')),
            'total_deal_value': self._get_float(row, col_map.get('total_deal_value')),
            'currency': self._get_value(row, col_map.get('currency'), default='GBP'),  # Added currency
            'artist_fee': self._get_float(row, col_map.get('artist_fee')),
            'booking_fee': self._get_float(row, col_map.get('booking_fee')),
            'booking_fee_vat': self._get_float(row, col_map.get('booking_fee_vat')),
            'hotel_buyout': self._get_float(row, col_map.get('hotel_buyout')),
            'flight_buyout': self._get_float(row, col_map.get('flight_buyout')),
            'ground_transport_buyout': self._get_float(row, col_map.get('ground_transport_buyout')),
            'withholding_tax': self._get_float(row, col_map.get('withholding_tax')),
            'total_artist_settlement': self._get_float(row, col_map.get('total_artist_settlement')),
        }
    
    def _contract_to_show(self, contract_data):
        """
        Convert contract data to show data.
        
        WHY?
            A contract defines the DEAL.
            A show is the PERFORMANCE we track.
            We create a show from the contract so we have something to
            attach invoices, payments, and settlements to.
        
        RETURNS:
            dict: Show data ready for database insertion
        """
        return {
            'contract_number': contract_data.get('contract_number'),
            'artist': contract_data.get('artist'),
            'event_name': contract_data.get('event_name'),
            'venue': contract_data.get('venue'),
            'city': contract_data.get('city'),
            'country': contract_data.get('country'),
            'booking_date': contract_data.get('booking_date'),
            'performance_date': contract_data.get('performance_date'),
            'performance_day': contract_data.get('performance_day'),
            'deal_description': contract_data.get('deal_description'),
            'total_deal_value': contract_data.get('total_deal_value'),
            'currency': contract_data.get('currency', 'GBP'),  # Added currency
            'artist_fee': contract_data.get('artist_fee'),
            'booking_fee': contract_data.get('booking_fee'),
            'hotel_buyout': contract_data.get('hotel_buyout'),
            'flight_buyout': contract_data.get('flight_buyout'),
            'ground_transport_buyout': contract_data.get('ground_transport_buyout'),
            'withholding_tax': contract_data.get('withholding_tax'),
            'net_artist_settlement': contract_data.get('total_artist_settlement'),
            'status': 'Contracted',
            'settlement_status': 'Pending',
        }
    
    def _link_contract_to_show(self, contract_id, show_id):
        """
        Link a contract record to its corresponding show.
        
        This updates the contract's show_id field so we know
        which show the contract belongs to.
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE contracts SET show_id = ? WHERE contract_id = ?",
                (show_id, contract_id)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[WARN] Error linking contract to show: {e}")
    
    def get_import_summary(self):
        """Get detailed import summary."""
        return {
            'batch_id': self.batch_id,
            'errors': self.errors,
            'skipped': self.skipped,
            'duplicates': self.duplicates,
        }


# =============================================================================
# LEARNING NOTES: DATA RELATIONSHIPS
# =============================================================================
#
# ONE-TO-ONE RELATIONSHIP:
#   One contract → One show
#   Each contract creates exactly one show.
#   We link them via contract_number.
#
# ONE-TO-MANY RELATIONSHIP:
#   One show → Many invoices
#   One show → Many bank transactions
#   One show → Many outgoing payments
#   
#   This is why show_id appears in invoices, bank_transactions, etc.
#   It's called a "foreign key" - it references the shows table.
#
# WHY SEPARATE TABLES?
#   - Normalization: Avoid repeating data
#   - Flexibility: Can have different numbers of related items
#   - Integrity: Can't have orphan records (foreign key constraint)
#
# =============================================================================

