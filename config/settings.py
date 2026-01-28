# =============================================================================
# config/settings.py
# =============================================================================
# PURPOSE:
#   Central configuration file for the entire application.
#   All "magic numbers", constants, and settings live here.
#   This makes it easy to change things without hunting through code.
#
# WHY CENTRALIZE SETTINGS?
#   1. Single source of truth - change once, affects everywhere
#   2. Easy to find what can be configured
#   3. No hardcoded values scattered in code
#   4. Makes testing easier (can swap configs)
# =============================================================================

# -----------------------------------------------------------------------------
# DATABASE CONFIGURATION
# -----------------------------------------------------------------------------
# SQLite database file path (relative to where you run the app)
# SQLite is a file-based database - no server needed, just a .db file
DB_PATH = "pinball.db"

# -----------------------------------------------------------------------------
# CURRENCY CONFIGURATION
# -----------------------------------------------------------------------------
# List of currencies we accept in the system
# Used for validation when importing data
ALLOWED_CURRENCIES = ["GBP", "EUR", "USD", "AUD"]

# Default currency if none specified
DEFAULT_CURRENCY = "GBP"

# Tolerance for matching amounts (handles floating point rounding)
# Example: £100.00 and £100.001 are considered equal
AMOUNT_TOLERANCE = 0.01

# -----------------------------------------------------------------------------
# INVOICE LINE ITEM TYPES (Account Codes)
# -----------------------------------------------------------------------------
# These are the types of charges that can appear on an invoice
# Each invoice can have multiple line items of different types
ACCOUNT_CODES = [
    "Booking Fee",      # Agency's fee for booking the artist
    "Artist Fee",       # The actual fee paid to the artist
    "Production",       # Stage/sound/lighting costs
    "Buyouts",          # Flat fees instead of royalties
    "Withholding Tax",  # Tax withheld at source (international)
    "Work Permits",     # Visa/permit costs
    "Hotel",            # Accommodation costs
    "Flights",          # Travel costs
    "Ground Transport", # Cars, taxis, etc.
    "Per Diem",         # Daily allowance for artist
]

# -----------------------------------------------------------------------------
# ENTITIES (Who sends invoices)
# -----------------------------------------------------------------------------
# These are the companies that can issue invoices
FROM_ENTITIES = [
    "Arcade Talent Agency Ltd",
    "SHUBOSTAR Ltd",
    "Kerri Chandler Management"
]

# -----------------------------------------------------------------------------
# AGENTS
# -----------------------------------------------------------------------------
# List of agents who book shows
AGENTS = [
    "Angelo",
    "Sarah",
    "Mike",
    "Emma"
]

# -----------------------------------------------------------------------------
# PAYMENT DESTINATIONS
# -----------------------------------------------------------------------------
# Where payments can be sent
PAYMENT_DESTINATIONS = [
    "Arcade Account",      # Money goes to agency first
    "Direct to Artist",    # Money goes straight to artist
]

# -----------------------------------------------------------------------------
# PAYMENT TYPES (Outgoing)
# -----------------------------------------------------------------------------
# Types of payments the agency makes OUT
OUTGOING_PAYMENT_TYPES = [
    "Artist Advance",           # Early payment to artist before show
    "Artist Final Settlement",  # Final payment after show
    "Hotel",                    # Hotel booking payment
    "Flights",                  # Flight booking payment
    "Ground Transport",         # Car/taxi payment
    "Production",               # Stage/equipment payment
    "Other Expense",            # Miscellaneous
]

# -----------------------------------------------------------------------------
# SHOW STATUS OPTIONS
# -----------------------------------------------------------------------------
# The lifecycle of a show from booking to completion
SHOW_STATUSES = [
    "Contracted",       # Deal signed, not yet performed
    "Performed",        # Show has happened
    "Settled",          # All money reconciled
    "Cancelled",        # Show didn't happen
    "Disputed",         # There's a problem with payment
]

# -----------------------------------------------------------------------------
# SETTLEMENT STATUS OPTIONS
# -----------------------------------------------------------------------------
# Status of artist payment for a show
SETTLEMENT_STATUSES = [
    "Pending",          # Not yet paid
    "Partial",          # Some payment made
    "Paid",             # Fully paid
    "Overpaid",         # Paid too much (need to recover)
    "Confirmed",        # Artist confirmed receipt
]

# -----------------------------------------------------------------------------
# UI CONFIGURATION
# -----------------------------------------------------------------------------
PAGE_TITLE = "Arcade Pinball V3"
PAGE_ICON = "🎱"  # Pinball!
LAYOUT = "wide"

# -----------------------------------------------------------------------------
# DUPLICATE DETECTION RULES
# -----------------------------------------------------------------------------
# How we identify if something is a duplicate

# For invoices: same invoice number = duplicate
# For bank transactions: same date + amount + description = likely duplicate
# For contracts: same contract number = duplicate

DUPLICATE_DETECTION = {
    "invoices": {
        "key_fields": ["invoice_number"],  # These fields must be unique
        "warning_fields": ["total_gross", "contact_name"],  # Warn if these differ
    },
    "bank_transactions": {
        "key_fields": ["date", "amount", "description"],  # Combination must be unique
        "time_window_days": 1,  # Consider duplicates within this window
    },
    "contracts": {
        "key_fields": ["contract_number"],
    },
}


