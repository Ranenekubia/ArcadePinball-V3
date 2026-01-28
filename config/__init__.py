# =============================================================================
# config/__init__.py
# =============================================================================
# PURPOSE:
#   This file makes the 'config' folder a Python package.
#   It also provides convenient imports so other files can do:
#       from config import DB_PATH, CURRENCIES
#   Instead of:
#       from config.settings import DB_PATH, CURRENCIES
#
# WHAT IS __init__.py?
#   When Python sees a folder with __init__.py, it treats that folder as a
#   "package" (a collection of related modules). This file runs when you
#   import anything from the package.
# =============================================================================

# Import everything from settings.py and make it available at package level
from .settings import *

# The dot (.) means "from the current package" - i.e., from config/settings.py


