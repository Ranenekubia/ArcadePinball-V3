# =============================================================================
# utils/__init__.py
# =============================================================================
# PURPOSE:
#   Makes the utils folder a Python package and provides easy imports.
#   
# WHAT ARE UTILS?
#   "Utils" is short for "utilities" - helper functions that are used
#   across the application. They don't belong to any specific feature
#   but are useful everywhere.
#
# EXAMPLES:
#   - Calculation functions (reconciliation status, totals)
#   - Formatting functions (dates, currency)
#   - Validation functions (check if data is valid)
# =============================================================================

from .calculations import (
    calculate_payment_status,
    calculate_invoice_status,
    calculate_show_settlement,
    calculate_reconciliation_summary,
)


