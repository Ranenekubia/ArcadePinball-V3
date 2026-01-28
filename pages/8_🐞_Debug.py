# =============================================================================
# pages/8_🐞_Debug.py
# =============================================================================
# PURPOSE:
#   Debug page to view all database tables and their contents.
#   Useful for troubleshooting and verifying data integrity.
#
# WHAT IT SHOWS:
#   - List of all tables in the database
#   - Schema (column names and types) for each table
#   - Row count and sample data for each table
#   - Option to view full table data
#
# IMPORTANT:
#   This page should be used for debugging only and might contain sensitive data.
# =============================================================================

import streamlit as st
import pandas as pd
from database.connection import get_db_connection
from database.schema import get_table_info

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Debug - Pinball V3",
    page_icon="🐞",
    layout="wide"
)

# -----------------------------------------------------------------------------
# PAGE HEADER
# -----------------------------------------------------------------------------
st.title("🐞 Debug - Database Viewer")
st.caption("View all database tables and their contents for debugging purposes.")

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------
def get_table_names():
    """Get list of all tables in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables

def get_table_row_count(table_name):
    """Get row count for a table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_table_data(table_name, limit=100):
    """Get data from a table (with optional limit)."""
    conn = get_db_connection()
    df = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT {limit}", conn)
    conn.close()
    return df

def get_table_schema(table_name):
    """Get schema information for a table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    schema = cursor.fetchall()
    conn.close()
    return schema

# -----------------------------------------------------------------------------
# MAIN CONTENT
# -----------------------------------------------------------------------------

# Get all tables
tables = get_table_names()

if not tables:
    st.error("No tables found in the database!")
    st.stop()

# Show table summary
st.write("### 📊 Database Summary")
st.write(f"Found **{len(tables)}** tables in the database.")

# Create tabs for each table
tabs = st.tabs([f"📋 {table}" for table in tables])

for i, table_name in enumerate(tables):
    with tabs[i]:
        st.write(f"#### Table: `{table_name}`")
        
        # Get row count
        row_count = get_table_row_count(table_name)
        st.metric("Row Count", row_count)
        
        # Show schema
        st.write("##### Schema")
        schema = get_table_schema(table_name)
        schema_df = pd.DataFrame(schema, columns=['cid', 'name', 'type', 'notnull', 'default_value', 'pk'])
        st.dataframe(schema_df, use_container_width=True)
        
        # Show data preview
        st.write("##### Data Preview (first 100 rows)")
        if row_count > 0:
            df = get_table_data(table_name, limit=100)
            st.dataframe(df, use_container_width=True)
            
            # Show some basic stats if there are numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            if numeric_cols:
                st.write("###### Numeric Column Summary")
                st.dataframe(df[numeric_cols].describe(), use_container_width=True)
        else:
            st.info("Table is empty.")
        
        # Option to view more rows
        if row_count > 100:
            st.warning(f"Table has {row_count} rows. Only showing first 100 rows.")
            if st.button(f"Load all {row_count} rows", key=f"load_all_{table_name}"):
                df_full = get_table_data(table_name, limit=row_count)
                st.dataframe(df_full, use_container_width=True)
                st.success(f"Loaded all {row_count} rows.")

# -----------------------------------------------------------------------------
# DATABASE INFORMATION
# -----------------------------------------------------------------------------
st.write("---")
st.write("### ℹ️ Database Information")

col1, col2 = st.columns(2)

with col1:
    st.write("##### Connection Info")
    st.code("""
    Database: SQLite (file-based)
    File: pinball.db
    Location: Same directory as app.py
    """)

with col2:
    st.write("##### Quick Actions")
    
    if st.button("🔄 Refresh All Data", use_container_width=True):
        st.rerun()
    
    if st.button("📋 Copy Table List", use_container_width=True):
        table_list_str = "\n".join(tables)
        st.code(table_list_str)
        st.success("Table list copied to code block above.")
    
    if st.button("📄 Export Schema", use_container_width=True):
        schema_info = get_table_info()
        st.json(schema_info)
        st.success("Schema exported as JSON above.")

# -----------------------------------------------------------------------------
# RAW SQL QUERY (Optional)
# -----------------------------------------------------------------------------
st.write("---")
st.write("### 🔍 Raw SQL Query")

query = st.text_area("Enter SQL query (READ-ONLY):", 
                     value="SELECT * FROM shows LIMIT 10",
                     height=100)

if st.button("Execute Query", type="primary"):
    try:
        conn = get_db_connection()
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        st.write("#### Query Results")
        st.dataframe(df, use_container_width=True)
        st.success(f"Query returned {len(df)} rows.")
    except Exception as e:
        st.error(f"Query error: {e}")

# -----------------------------------------------------------------------------
# LEARNING NOTES
# -----------------------------------------------------------------------------
st.write("---")
with st.expander("📚 Learning Notes: Database Debugging"):
    st.write("""
    **Why a debug page is useful:**
    1. **Verify Data Integrity**: Check that data is being stored correctly.
    2. **Troubleshoot Issues**: See exactly what's in the database when something goes wrong.
    3. **Understand Schema**: Review table structures and relationships.
    4. **Development Aid**: Quickly view data during development without external tools.

    **Security Considerations:**
    - This page should be protected in a production environment.
    - It exposes all data, including potentially sensitive information.
    - Consider adding authentication or removing this page in production.

    **SQLite Tips:**
    - Use `PRAGMA table_info(table_name)` to get column details.
    - `sqlite_master` is a system table containing metadata about all objects.
    - Always use parameterized queries to prevent SQL injection (not needed here since we only do read-only queries).
    """)

# =============================================================================
# END OF DEBUG PAGE
# =============================================================================