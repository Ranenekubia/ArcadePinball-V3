# =============================================================================
# pages/4_Shows.py
# =============================================================================
# PURPOSE:
#   View and search all shows. Drill-down: list/grid → click show → full detail.
#
# STRUCTURE:
#   - Main page: list/grid of shows (one page)
#   - Click a show → full detailed show view
#   - Detail view: all show info, connected invoices, payment info, related data
#   - Back to list → return to shows list
# =============================================================================

import streamlit as st
import pandas as pd
from datetime import datetime
from database import (
    init_db,
    load_shows,
    load_invoices,
    load_handshakes,
    load_outgoing_payments,
)
from utils import calculate_show_settlement
from utils.styling import apply_minimal_style
from config import SHOW_STATUSES, SETTLEMENT_STATUSES, AGENTS

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Shows - Pinball V3",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="expanded"
)

apply_minimal_style()
init_db()

# Session state: when set, show detail view for this show_id; when None, show list
DETAIL_KEY = "shows_detail_id"
if DETAIL_KEY not in st.session_state:
    st.session_state[DETAIL_KEY] = None

# -----------------------------------------------------------------------------
# DETAIL VIEW (drill-down: full show info + invoices + payments)
# -----------------------------------------------------------------------------
if st.session_state.get(DETAIL_KEY) is not None:
    selected_show_id = st.session_state[DETAIL_KEY]

    # Back button
    if st.button("← Back to list", key="back_to_list"):
        st.session_state.pop(DETAIL_KEY, None)
        st.rerun()

    st.write("---")

    # Load all data for this show
    shows_df = load_shows()
    invoices_df = load_invoices()
    handshakes_df = load_handshakes()
    outgoing_df = load_outgoing_payments()

    settlement = calculate_show_settlement(
        selected_show_id,
        shows_df,
        invoices_df,
        handshakes_df,
        outgoing_df
    )

    if settlement:
        st.title(f"🎭 {settlement['artist']} — {settlement['event_name'] or settlement['venue'] or 'Show'}")
        st.caption(f"Show #{selected_show_id} · Contract {settlement['contract_number'] or 'N/A'} · {settlement['performance_date'] or 'TBC'}")

        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 Overview", "💰 Money In (Invoices & Payments)", "💸 Money Out", "🎭 Artist Settlement"
        ])

        with tab1:
            st.write("### Show information")
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Details**")
                st.write(f"- **Contract:** {settlement['contract_number'] or 'N/A'}")
                st.write(f"- **Artist:** {settlement['artist']}")
                st.write(f"- **Event:** {settlement['event_name'] or 'N/A'}")
                st.write(f"- **Venue:** {settlement['venue'] or 'N/A'}")
                st.write(f"- **Date:** {settlement['performance_date'] or 'TBC'}")
                st.write(f"- **Status:** {settlement.get('status') or 'N/A'}")
                st.write(f"- **Settlement status:** {settlement.get('settlement_status') or 'N/A'}")
            with col2:
                st.write("**Deal terms**")
                st.write(f"- **Deal:** {settlement['deal_description'] or 'N/A'}")
                st.write(f"- **Total value:** £{settlement['total_deal_value']:,.2f}")
                st.write(f"- **Artist fee:** £{settlement['artist_fee']:,.2f}")
                st.write(f"- **Booking fee:** £{settlement['booking_fee']:,.2f}")

            st.write("---")
            st.write("**Status**")
            c1, c2, c3 = st.columns(3)
            with c1:
                status_color = "🟢" if settlement['promoter_status'] == "PAID" else "🟡" if settlement['promoter_status'] == "PART PAID" else "🔴"
                st.metric("Promoter", f"{status_color} {settlement['promoter_status']}")
            with c2:
                status_color = "🟢" if settlement['artist_status'] == "SETTLED" else "🟡" if settlement['artist_status'] == "PARTIAL" else "🔴"
                st.metric("Artist", f"{status_color} {settlement['artist_status']}")
            with c3:
                st.metric("Overall", settlement['overall_status'])

        with tab2:
            st.write("### Connected invoices")
            st.metric("Total invoiced", f"£{settlement['total_invoiced']:,.2f}")
            if settlement['invoices']:
                inv_df = pd.DataFrame(settlement['invoices'])
                cols = [c for c in ['invoice_number', 'total_gross', 'currency', 'is_paid'] if c in inv_df.columns]
                st.dataframe(inv_df[cols] if cols else inv_df, use_container_width=True, hide_index=True)
            else:
                st.info("No invoices for this show.")

            st.write("---")
            st.write("### Payments received")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Received", f"£{settlement['total_received']:,.2f}")
            with c2:
                st.metric("Outstanding", f"£{settlement['outstanding_from_promoter']:,.2f}")
            with c3:
                st.metric("Promoter status", settlement['promoter_status'])

        with tab3:
            st.write("### Payment information (money out)")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Artist", f"£{settlement['artist_payments']:,.2f}")
            with c2:
                st.metric("Hotel", f"£{settlement['hotel_payments']:,.2f}")
            with c3:
                st.metric("Flights", f"£{settlement['flight_payments']:,.2f}")
            with c4:
                st.metric("Other", f"£{settlement['other_payments']:,.2f}")
            st.metric("Total paid out", f"£{settlement['total_paid_out']:,.2f}")

            if settlement['outgoing_payments']:
                out_df = pd.DataFrame(settlement['outgoing_payments'])
                st.dataframe(out_df, use_container_width=True, hide_index=True)
            else:
                st.info("No outgoing payments recorded for this show.")

        with tab4:
            st.write("### Artist settlement")
            st.write(f"**Artist fee:** £{settlement['artist_fee']:,.2f}")
            if settlement['hotel_buyout'] > 0:
                st.write(f"- Hotel buyout: -£{settlement['hotel_buyout']:,.2f}")
            if settlement['flight_buyout'] > 0:
                st.write(f"- Flight buyout: -£{settlement['flight_buyout']:,.2f}")
            if settlement['withholding_tax'] > 0:
                st.write(f"- Withholding tax: -£{settlement['withholding_tax']:,.2f}")
            st.write("---")
            st.write(f"**Net due to artist:** £{settlement['net_artist_due']:,.2f}")
            st.write(f"Already paid: £{settlement['artist_paid']:,.2f}")
            st.write(f"**Balance: £{settlement['artist_balance']:,.2f}**")
            if settlement['artist_status'] == "SETTLED":
                st.success("✅ Artist fully paid")
            elif settlement['artist_status'] == "PARTIAL":
                st.warning(f"🟡 Partial. £{settlement['artist_balance']:,.2f} remaining.")
            else:
                st.error(f"🔴 Pending. £{settlement['artist_balance']:,.2f} due.")
    else:
        st.warning("Show not found or no settlement data.")
        if st.button("← Back to list", key="back_to_list_2"):
            st.session_state.pop(DETAIL_KEY, None)
            st.rerun()

    st.stop()

# -----------------------------------------------------------------------------
# LIST VIEW (main page: grid of shows)
# -----------------------------------------------------------------------------
st.title("Shows")
st.caption("Click a show to open full details (invoices, payments, settlement).")

# Search and filters
st.write("### 🔍 Search & Filter")
col1, col2, col3, col4 = st.columns(4)
with col1:
    search_text = st.text_input("Search", placeholder="Artist, venue, promoter, contract...", help="Search across multiple fields")
with col2:
    status_filter = st.selectbox("Show status", options=["All"] + SHOW_STATUSES)
with col3:
    settlement_filter = st.selectbox("Settlement status", options=["All"] + SETTLEMENT_STATUSES)
with col4:
    agent_filter = st.selectbox("Agent", options=["All"] + AGENTS)

filters = {}
if status_filter != "All":
    filters['status'] = status_filter
if settlement_filter != "All":
    filters['settlement_status'] = settlement_filter
if agent_filter != "All":
    filters['agent'] = agent_filter

shows_df = load_shows(search=search_text if search_text else None, filters=filters if filters else None)

# Attach invoice counts
invoices_df = load_invoices()
if not invoices_df.empty:
    inv_with_show = invoices_df[invoices_df['show_id'].notna()].copy()
    if not inv_with_show.empty:
        inv_with_show['show_id'] = inv_with_show['show_id'].astype(int)
        show_inv = inv_with_show.groupby('show_id').size().reset_index(name='invoice_count')
        shows_df = shows_df.merge(show_inv, how='left', on='show_id')
    else:
        shows_df['invoice_count'] = 0
else:
    shows_df['invoice_count'] = 0
shows_df['invoice_count'] = shows_df['invoice_count'].fillna(0).astype(int)

# List/grid
st.write("---")
st.write(f"### 📋 Shows ({len(shows_df)} found)")

if len(shows_df) == 0:
    st.info("No shows found. Adjust search or filters, or import contracts on the Import page.")
    st.stop()

def open_detail(show_id):
    st.session_state[DETAIL_KEY] = show_id

# Grid: 3 columns of cards
CARDS_PER_ROW = 3
for i in range(0, len(shows_df), CARDS_PER_ROW):
    row_shows = shows_df.iloc[i : i + CARDS_PER_ROW]
    cols = st.columns(CARDS_PER_ROW)
    for j, (_, row) in enumerate(row_shows.iterrows()):
        with cols[j]:
            sid = int(row['show_id'])
            artist = row.get('artist') or '—'
            venue = row.get('venue') or '—'
            event = row.get('event_name') or venue
            date_val = row.get('performance_date') or 'TBC'
            status = row.get('status') or '—'
            inv_count = int(row.get('invoice_count', 0))
            deal = row.get('total_deal_value')
            deal_str = f"£{deal:,.2f}" if pd.notna(deal) and deal else "—"

            with st.container():
                st.write(f"**{artist}**")
                st.caption(f"{event}")
                st.caption(f"{venue} · {date_val}")
                st.caption(f"Status: {status} · Invoices: {inv_count} · {deal_str}")
                st.button("View full detail", key=f"view_{sid}", on_click=open_detail, args=(sid,), use_container_width=True)
                st.write("---")

# Export
st.write("---")
csv = shows_df.to_csv(index=False)
st.download_button(
    label="📥 Export CSV",
    data=csv,
    file_name=f"shows_export_{datetime.now().strftime('%Y%m%d')}.csv",
    mime="text/csv",
    key="export_shows"
)
