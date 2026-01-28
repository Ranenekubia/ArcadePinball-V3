# =============================================================================
# database/connection.py
# =============================================================================
# PURPOSE:
#   Handles database connections. This is the ONLY file that knows how to
#   connect to the database. All other code uses this function.
#
# WHY CENTRALIZE CONNECTION?
#   1. If we change databases (SQLite → PostgreSQL), only this file changes
#   2. We can add connection pooling later without changing other code
#   3. Easier to add logging, error handling, etc.
#
# SQLITE BASICS:
#   - SQLite is a file-based database (no server needed)
#   - Each connection opens the .db file
#   - You should close connections when done (or use 'with' statement)
#   - SQLite handles multiple readers but only one writer at a time
# =============================================================================

import sqlite3  # Built into Python, no pip install needed!
from config import DB_PATH  # Import our database path from config


def get_db_connection():
    """
    Create and return a connection to the SQLite database.
    
    WHAT THIS DOES:
        1. Opens (or creates) the database file specified in DB_PATH
        2. Enables foreign key support (important for data integrity)
        3. Returns the connection object
    
    USAGE:
        # Method 1: Manual close (must remember to close!)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM shows")
        results = cursor.fetchall()
        conn.close()  # Don't forget this!
        
        # Method 2: Context manager (auto-closes) - PREFERRED
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM shows")
            results = cursor.fetchall()
        # Connection automatically closed here
    
    RETURNS:
        sqlite3.Connection: A connection object to the database
    
    NOTES:
        - The database file is created automatically if it doesn't exist
        - Foreign keys are OFF by default in SQLite, we turn them ON
        - Each call creates a NEW connection (no pooling yet)
    """
    
    # sqlite3.connect() opens the database file
    # If the file doesn't exist, SQLite creates it automatically
    conn = sqlite3.connect(DB_PATH)
    
    # IMPORTANT: Enable foreign key constraints
    # By default, SQLite ignores foreign keys! We need to turn them on.
    # Foreign keys ensure data integrity (can't reference non-existent records)
    conn.execute("PRAGMA foreign_keys = ON")
    
    # Return the connection for the caller to use
    return conn


# =============================================================================
# ADDITIONAL NOTES FOR LEARNING:
# =============================================================================
#
# WHAT IS A DATABASE CONNECTION?
#   Think of it like a phone call to the database. You "dial" (connect),
#   "talk" (execute queries), and "hang up" (close). While connected,
#   you can send multiple queries.
#
# WHAT IS A CURSOR?
#   A cursor is like a pointer that moves through query results.
#   You use it to execute queries and fetch results row by row.
#   
#   conn = get_db_connection()
#   cursor = conn.cursor()           # Create a cursor
#   cursor.execute("SELECT * ...")   # Execute a query
#   row = cursor.fetchone()          # Get one row
#   rows = cursor.fetchall()         # Get all rows
#
# WHAT IS PRAGMA?
#   PRAGMA is SQLite's way of configuring the database.
#   "PRAGMA foreign_keys = ON" tells SQLite to enforce foreign key rules.
#
# WHAT ARE FOREIGN KEYS?
#   A foreign key links a column in one table to a column in another.
#   Example: invoice.show_id → shows.show_id
#   This ensures every invoice references a real show that exists.
#
# =============================================================================


