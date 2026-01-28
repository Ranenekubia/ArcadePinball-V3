# =============================================================================
# pages/7_🤝_Handshakes.py
# =============================================================================
# PURPOSE:
#   View and manage handshakes (bank-to-invoice matches).
#   This shows all the reconciliation work that's been done.
#
# FEATURES:
#   - View all matches
#   - Search and filter
#   - Delete incorrect matches
#   - Summary statistics
# =============================================================================

import streamlit as st
import pandas as pd
from database import (
    init_db,
    load_handshakes,
    delete_handshake
)

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Handshakes - Pinball V3",
    page_icon="🤝",
    layout="wide"
)

init_db()

# -----------------------------------------------------------------------------
# PAGE HEADER
# -----------------------------------------------------------------------------
st.title("🤝 Handshakes")
st.caption("View and manage bank-to-invoice matches.")

# -----------------------------------------------------------------------------
# LOAD DATA
# -----------------------------------------------------------------------------
handshakes_df = load_handshakes()

if len(handshakes_df) == 0:
    st.info("📭 No handshakes created yet.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔗 Go to Match Page", use_container_width=True):
            st.switch_page("pages/3_🔗_Match.py")
    with col2:
        if st.button("📥 Import Data First", use_container_width=True):
            st.switch_page("pages/2_📥_Import.py")
    
    st.stop()

# -----------------------------------------------------------------------------
# SEARCH AND FILTER
# -----------------------------------------------------------------------------
st.write("### 🔍 Search & Filter")

col1, col2 = st.columns([3, 1])

with col1:
    search = st.text_input(
        "Search",
        placeholder="Search by invoice number, description, or note...",
        label_visibility="collapsed"
    )

with col2:
    filter_option = st.selectbox(
        "Filter",
        options=["All", "With Proxy", "No Proxy", "With Notes"],
        label_visibility="collapsed"
    )

# Apply filters
filtered_df = handshakes_df.copy()

if search:
    filtered_df = filtered_df[
        (filtered_df['invoice_number'].str.contains(search, case=False, na=False)) |
        (filtered_df['bank_desc'].str.contains(search, case=False, na=False)) |
        (filtered_df['note'].fillna('').str.contains(search, case=False, na=False))
    ]

if filter_option == "With Proxy":
    filtered_df = filtered_df[filtered_df['proxy_amount'] != 0]
elif filter_option == "No Proxy":
    filtered_df = filtered_df[filtered_df['proxy_amount'] == 0]
elif filter_option == "With Notes":
    filtered_df = filtered_df[filtered_df['note'].notna() & (filtered_df['note'] != '')]

# -----------------------------------------------------------------------------
# SUMMARY STATS
# -----------------------------------------------------------------------------
st.write("---")
st.write("### 📊 Summary")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Matches", len(handshakes_df))

with col2:
    with_proxy = len(handshakes_df[handshakes_df['proxy_amount'] != 0])
    st.metric("With Proxy", with_proxy)

with col3:
    total_banked = handshakes_df['bank_amount_applied'].sum()
    st.metric("Total Matched", f"£{total_banked:,.2f}")

with col4:
    total_proxy = handshakes_df['proxy_amount'].sum()
    st.metric("Total Proxy", f"£{total_proxy:,.2f}")

# -----------------------------------------------------------------------------
# HANDSHAKES LIST
# -----------------------------------------------------------------------------
st.write("---")
st.write(f"### 📋 Matches ({len(filtered_df)} shown)")

if len(filtered_df) == 0:
    st.info("No matches found with current filters.")
else:
    for idx, row in filtered_df.iterrows():
        with st.container():
            col1, col2 = st.columns([10, 1])
            
            with col1:
                # Header line
                st.write(
                    f"**#{row['handshake_id']}** | "
                    f"Bank #{row['bank_id']} → Invoice {row['invoice_number']}"
                )
                
                # Details in columns
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    st.caption(f"💳 Bank: {row['bank_currency']} {row['bank_amount_applied']:,.2f}")
                    st.caption(f"📄 Invoice: {row['invoice_currency']} {row['invoice_total']:,.2f}")
                
                with col_b:
                    if row['proxy_amount'] != 0:
                        st.caption(f"🔧 Proxy: {row['proxy_amount']:,.2f}")
                    total_applied = row['bank_amount_applied'] + row['proxy_amount']
                    st.caption(f"✅ Applied: {row['bank_currency']} {total_applied:,.2f}")
                
                with col_c:
                    st.caption(f"📅 {row['created_at']}")
                    if row['note']:
                        st.caption(f"📝 {row['note']}")
            
            with col2:
                # Delete button
                if st.button("🗑️", key=f"del_{row['handshake_id']}", help="Delete this match"):
                    # Confirmation pattern
                    confirm_key = f"confirm_del_{row['handshake_id']}"
                    if st.session_state.get(confirm_key):
                        delete_handshake(row['handshake_id'])
                        st.success("Deleted!")
                        st.session_state[confirm_key] = False
                        st.rerun()
                    else:
                        st.session_state[confirm_key] = True
                        st.warning("Click again to confirm")
            
            st.write("---")

# -----------------------------------------------------------------------------
# EXPORT
# -----------------------------------------------------------------------------
st.write("### 📥 Export")

csv = handshakes_df.to_csv(index=False)
st.download_button(
    label="📥 Download All Matches (CSV)",
    data=csv,
    file_name=f"handshakes_export_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
    mime="text/csv"
)


# =============================================================================
# LEARNING NOTES: DELETE PATTERNS
# =============================================================================
#
# SAFE DELETE:
#   Deleting data is dangerous - it can't be undone easily.
#   Best practices:
#   
#   1. CONFIRMATION: Require a second click or type "DELETE"
#   2. SOFT DELETE: Mark as deleted instead of removing
#   3. CASCADING: Handle related records properly
#   4. AUDIT: Log who deleted what and when
#
# OUR APPROACH:
#   - Two-click confirmation (first click warns, second deletes)
#   - Hard delete (actually removes from database)
#   - Cascade handled in delete_handshake() function
#   - Immediate feedback with st.rerun()
#
# ALTERNATIVE: SOFT DELETE
#   Instead of DELETE FROM table, do:
#   UPDATE table SET is_deleted = 1, deleted_at = NOW()
#   
#   Then filter out deleted records in queries:
#   SELECT * FROM table WHERE is_deleted = 0
#
# =============================================================================


