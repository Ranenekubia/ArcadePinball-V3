# =============================================================================
# pages/1_📊_Dashboard.py
# =============================================================================
# PURPOSE:
#   The main dashboard - gives an overview of all data at a glance.
#   This is the "home" page users see when they open the app.
#
# WHAT IT SHOWS:
#   - Quick stats (total shows, invoices, payments, etc.)
#   - Payment status overview (how many paid/unpaid)
#   - Action items (what needs attention)
#   - Recent activity
#
# WHY A DASHBOARD?
#   Users need a quick way to see:
#   - "Is everything okay?"
#   - "What needs my attention?"
#   - "What's the overall status?"
#   
#   A dashboard answers these questions at a glance.
# =============================================================================

import streamlit as st
import pandas as pd
from database import (
    init_db,
    load_shows,
    load_invoices,
    load_bank_transactions,
    load_handshakes,
    load_settlements,
    load_outgoing_payments
)
from utils import calculate_reconciliation_summary
from utils.styling import apply_minimal_style

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard - Pinball V3",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply minimal styling
apply_minimal_style()

# -----------------------------------------------------------------------------
# INITIALIZE DATABASE
# -----------------------------------------------------------------------------
# This creates tables if they don't exist.
# Safe to call every time - it won't delete existing data.
init_db()

# -----------------------------------------------------------------------------
# PAGE HEADER
# -----------------------------------------------------------------------------
st.title("Dashboard")
st.caption("Overview of your show reconciliation data")

# -----------------------------------------------------------------------------
# LOAD ALL DATA
# -----------------------------------------------------------------------------
# We load everything upfront so we can calculate stats.
# In a larger app, you might optimize this with caching.

shows_df = load_shows()
invoices_df = load_invoices()
bank_df = load_bank_transactions()
handshakes_df = load_handshakes()
settlements_df = load_settlements()
outgoing_df = load_outgoing_payments()

# -----------------------------------------------------------------------------
# QUICK STATS ROW
# -----------------------------------------------------------------------------
# Show key metrics at the top of the page.
# st.metric() displays a number with optional delta (change indicator).

st.write("### Quick Stats")

# Create 5 columns for stats
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        label="🎭 Shows",
        value=len(shows_df),
        help="Total shows in the system"
    )

with col2:
    st.metric(
        label="📄 Invoices",
        value=len(invoices_df),
        help="Total invoices created"
    )

with col3:
    st.metric(
        label="💳 Bank Transactions",
        value=len(bank_df),
        help="Total bank transactions imported"
    )

with col4:
    st.metric(
        label="🤝 Matches",
        value=len(handshakes_df),
        help="Bank-to-invoice matches created"
    )

with col5:
    # Calculate how many invoices are fully paid
    if len(invoices_df) > 0 and len(handshakes_df) > 0:
        summary = calculate_reconciliation_summary(invoices_df, handshakes_df)
        paid_count = len(summary[summary['status'] == 'PAID'])
        st.metric(
            label="✅ Paid Invoices",
            value=f"{paid_count}/{len(invoices_df)}",
            delta=f"{(paid_count/len(invoices_df)*100):.0f}%",
            help="Fully paid invoices"
        )
    else:
        st.metric(label="✅ Paid Invoices", value="0/0")

# -----------------------------------------------------------------------------
# PAYMENT STATUS OVERVIEW
# -----------------------------------------------------------------------------
# Visual breakdown of invoice payment statuses.

if len(invoices_df) > 0:
    st.write("---")
    st.write("### Payment Status")
    
    if len(handshakes_df) > 0:
        summary = calculate_reconciliation_summary(invoices_df, handshakes_df)
        status_counts = summary['status'].value_counts()
    else:
        # No payments yet, all unpaid
        status_counts = pd.Series({'UNPAID': len(invoices_df)})
    
    # Display status counts
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        unpaid = status_counts.get('UNPAID', 0)
        st.metric(
            "⚠️ UNPAID",
            unpaid,
            delta=f"-{unpaid}" if unpaid > 0 else None,
            delta_color="inverse"  # Red for negative
        )
    
    with col2:
        part_paid = status_counts.get('PART PAID', 0)
        st.metric("🟡 PART PAID", part_paid)
    
    with col3:
        paid = status_counts.get('PAID', 0)
        st.metric(
            "✅ PAID",
            paid,
            delta=f"+{paid}" if paid > 0 else None,
            delta_color="normal"  # Green for positive
        )
    
    with col4:
        overpaid = status_counts.get('OVERPAID', 0)
        st.metric("🔴 OVERPAID", overpaid)
    
    # Progress bar
    total = len(invoices_df)
    if total > 0:
        paid_pct = status_counts.get('PAID', 0) / total
        st.caption(f"Overall: {paid_pct*100:.0f}% fully paid")
        st.progress(paid_pct)

# -----------------------------------------------------------------------------
# SHOW STATUS OVERVIEW
# -----------------------------------------------------------------------------
if len(shows_df) > 0:
    st.write("---")
    st.write("### Show Status")
    
    show_status_counts = shows_df['status'].value_counts()
    settlement_status_counts = shows_df['settlement_status'].value_counts()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Show Status**")
        for status, count in show_status_counts.items():
            st.write(f"- {status}: {count}")
    
    with col2:
        st.write("**Settlement Status**")
        for status, count in settlement_status_counts.items():
            st.write(f"- {status}: {count}")

# -----------------------------------------------------------------------------
# ACTION REQUIRED
# -----------------------------------------------------------------------------
# Highlight items that need attention.

st.write("---")
st.write("### Action Required")

actions_needed = []

# Check for unpaid invoices
if len(invoices_df) > 0:
    if len(handshakes_df) > 0:
        summary = calculate_reconciliation_summary(invoices_df, handshakes_df)
        unpaid = summary[summary['status'] == 'UNPAID']
    else:
        unpaid = invoices_df
    
    if len(unpaid) > 0:
        total_outstanding = unpaid['total_gross'].sum()
        actions_needed.append(f"{len(unpaid)} invoices unpaid (£{total_outstanding:,.2f} outstanding)")

# Check for unmatched bank transactions
unmatched_bank = bank_df[bank_df['is_matched'] == 0] if len(bank_df) > 0 else pd.DataFrame()
if len(unmatched_bank) > 0:
    actions_needed.append(f"{len(unmatched_bank)} bank transactions need matching")

# Check for pending settlements
if len(settlements_df) > 0:
    pending = settlements_df[settlements_df['status'] == 'Pending']
    if len(pending) > 0:
        actions_needed.append(f"{len(pending)} artist settlements pending")

# Display actions or success message
if actions_needed:
    for action in actions_needed:
        st.warning(action)
else:
    if len(invoices_df) > 0:
        st.success("All caught up! No immediate actions needed.")
    else:
        st.info("Get started by importing data on the Import page.")

# -----------------------------------------------------------------------------
# RECENT ACTIVITY
# -----------------------------------------------------------------------------
st.write("---")
st.write("### Recent Activity")

if len(handshakes_df) > 0:
    # Show last 5 matches
    recent = handshakes_df.head(5)
    for _, row in recent.iterrows():
        with st.container():
            st.write(f"Bank #{row['bank_id']} → Invoice {row['invoice_number']} | {row['bank_currency']} {row['bank_amount_applied']:,.2f}")
            st.caption(f"Created: {row['created_at']}")
else:
    st.info("No recent activity. Create matches on the Match page.")

# -----------------------------------------------------------------------------
# QUICK NAVIGATION
# -----------------------------------------------------------------------------
st.write("---")
st.write("### Quick Actions")

col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("Import Data", use_container_width=True):
        st.switch_page("pages/2_Import.py")

with col2:
    if st.button("Match Payments", use_container_width=True):
        st.switch_page("pages/3_Match.py")

with col3:
    if st.button("View Shows", use_container_width=True):
        st.switch_page("pages/4_Shows.py")

with col4:
    if st.button("Settlement Report", use_container_width=True):
        st.switch_page("pages/6_Settlement.py")


# =============================================================================
# LEARNING NOTES: DASHBOARD DESIGN
# =============================================================================
#
# GOOD DASHBOARDS:
#   1. Show the most important info first
#   2. Use visual hierarchy (big numbers, colors)
#   3. Highlight what needs attention
#   4. Provide quick navigation to common tasks
#   5. Don't overwhelm - keep it simple
#
# STREAMLIT TIPS USED HERE:
#   - st.columns() for side-by-side layout
#   - st.metric() for key numbers
#   - st.progress() for visual progress
#   - st.warning/success/info for alerts
#   - st.button() for navigation
#
# =============================================================================


