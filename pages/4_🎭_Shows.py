# =============================================================================
# pages/4_🎭_Shows.py
# =============================================================================
# PURPOSE:
#   View and search all shows. This is the central "hub" view.
#   Shows are the anchor point - everything connects to a show.
#
# FEATURES:
#   - Search by artist, venue, promoter, contract number
#   - Filter by status, agent, date range
#   - View show details
#   - Quick links to related invoices/payments
#
# THIS ADDRESSES YOUR REQUIREMENT:
#   "Create a complete table with full show detail...
#    that can be searched by show, by agent, by artist, by promoter"
# =============================================================================

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import (
    init_db,
    load_shows,
    load_show_by_id,
    load_invoices,
    load_handshakes,
    load_outgoing_payments,
    load_settlements
)
from utils import calculate_show_settlement
from config import SHOW_STATUSES, SETTLEMENT_STATUSES, AGENTS

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Shows - Pinball V3",
    page_icon="🎭",
    layout="wide"
)

init_db()

# -----------------------------------------------------------------------------
# PAGE HEADER
# -----------------------------------------------------------------------------
st.title("🎭 Shows")
st.caption("View and search all shows. Click a show to see full details.")

# -----------------------------------------------------------------------------
# SEARCH AND FILTERS
# -----------------------------------------------------------------------------
st.write("### 🔍 Search & Filter")

col1, col2, col3, col4 = st.columns(4)

with col1:
    search_text = st.text_input(
        "Search",
        placeholder="Artist, venue, promoter, contract...",
        help="Search across multiple fields"
    )

with col2:
    status_filter = st.selectbox(
        "Show Status",
        options=["All"] + SHOW_STATUSES,
        help="Filter by show status"
    )

with col3:
    settlement_filter = st.selectbox(
        "Settlement Status",
        options=["All"] + SETTLEMENT_STATUSES,
        help="Filter by settlement status"
    )

with col4:
    agent_filter = st.selectbox(
        "Agent",
        options=["All"] + AGENTS,
        help="Filter by booking agent"
    )

# -----------------------------------------------------------------------------
# LOAD AND FILTER DATA
# -----------------------------------------------------------------------------

# Build filters dict
filters = {}
if status_filter != "All":
    filters['status'] = status_filter
if settlement_filter != "All":
    filters['settlement_status'] = settlement_filter
if agent_filter != "All":
    filters['agent'] = agent_filter

# Load shows with search and filters
shows_df = load_shows(search=search_text if search_text else None, filters=filters if filters else None)

# -----------------------------------------------------------------------------
# ATTACH INVOICE NUMBERS TO SHOWS
# -----------------------------------------------------------------------------
# Load invoices and group by show_id to get a list of invoice numbers for each show
invoices_df = load_invoices()
if not invoices_df.empty:
    # Filter out invoices without show_id
    invoices_with_show = invoices_df[invoices_df['show_id'].notna()].copy()
    if not invoices_with_show.empty:
        invoices_with_show['show_id'] = invoices_with_show['show_id'].astype(int)
        show_invoices = invoices_with_show.groupby('show_id')['invoice_number'].apply(list).reset_index()
        show_invoices.columns = ['show_id', 'invoice_numbers']
        shows_df = shows_df.merge(show_invoices, how='left', left_on='show_id', right_on='show_id')
    else:
        shows_df['invoice_numbers'] = [[] for _ in range(len(shows_df))]
else:
    shows_df['invoice_numbers'] = [[] for _ in range(len(shows_df))]

# Format the invoice numbers for display
def format_invoice_numbers(invoice_list):
    if not invoice_list:
        return "0"
    else:
        # Show the first 3 invoice numbers, then ...
        if len(invoice_list) <= 3:
            return f"{len(invoice_list)} ({', '.join(invoice_list)})"
        else:
            return f"{len(invoice_list)} ({', '.join(invoice_list[:3])}, ...)"

shows_df['invoices'] = shows_df['invoice_numbers'].apply(format_invoice_numbers)

# -----------------------------------------------------------------------------
# SHOW COUNT AND EXPORT
# -----------------------------------------------------------------------------
st.write("---")

col1, col2 = st.columns([3, 1])

with col1:
    st.write(f"### 📋 Shows ({len(shows_df)} found)")

with col2:
    if len(shows_df) > 0:
        # Export button
        csv = shows_df.to_csv(index=False)
        st.download_button(
            label="📥 Export CSV",
            data=csv,
            file_name=f"shows_export_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

# -----------------------------------------------------------------------------
# SHOWS TABLE
# -----------------------------------------------------------------------------
if len(shows_df) == 0:
    st.info("No shows found. Try adjusting your search or filters.")
    st.write("Or import contracts on the Import page to create shows.")
else:
    # Select which columns to display
    display_columns = [
        'show_id', 'contract_number', 'artist', 'event_name', 'venue',
        'performance_date', 'status', 'settlement_status', 'invoices',
        'total_deal_value', 'artist_fee', 'booking_fee'
    ]
    
    # Only include columns that exist
    available_columns = [c for c in display_columns if c in shows_df.columns]
    
    # Create display dataframe
    display_df = shows_df[available_columns].copy()
    
    # Format currency columns
    for col in ['total_deal_value', 'artist_fee', 'booking_fee']:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(
                lambda x: f"£{x:,.2f}" if pd.notna(x) and x != 0 else "-"
            )
    
    # Display table with selection
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "show_id": st.column_config.NumberColumn("ID", width="small"),
            "contract_number": "Contract",
            "artist": "Artist",
            "event_name": "Event",
            "venue": "Venue",
            "performance_date": "Date",
            "status": "Status",
            "settlement_status": "Settlement",
            "invoices": "Invoices",
            "total_deal_value": "Deal Value",
            "artist_fee": "Artist Fee",
            "booking_fee": "Booking Fee",
        }
    )
    
    # -----------------------------------------------------------------------------
    # SHOW DETAIL VIEW
    # -----------------------------------------------------------------------------
    st.write("---")
    st.write("### 📄 Show Detail")
    
    # Select a show to view details
    show_options = {
        row['show_id']: f"#{row['show_id']} - {row['artist']} @ {row['venue'] or 'TBC'}"
        for _, row in shows_df.iterrows()
    }
    
    selected_show_id = st.selectbox(
        "Select a show to view details:",
        options=list(show_options.keys()),
        format_func=lambda x: show_options[x]
    )
    
    if selected_show_id:
        # Load all data needed for settlement calculation
        invoices_df = load_invoices()
        handshakes_df = load_handshakes()
        outgoing_df = load_outgoing_payments()
        
        # Calculate full settlement
        settlement = calculate_show_settlement(
            selected_show_id,
            shows_df,
            invoices_df,
            handshakes_df,
            outgoing_df
        )
        
        if settlement:
            # Display in tabs
            tab1, tab2, tab3, tab4 = st.tabs([
                "📋 Overview", "💰 Money In", "💸 Money Out", "🎭 Artist Settlement"
            ])
            
            with tab1:
                # Show overview
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Show Details**")
                    st.write(f"- Contract: {settlement['contract_number'] or 'N/A'}")
                    st.write(f"- Artist: {settlement['artist']}")
                    st.write(f"- Event: {settlement['event_name'] or 'N/A'}")
                    st.write(f"- Venue: {settlement['venue'] or 'N/A'}")
                    st.write(f"- Date: {settlement['performance_date'] or 'TBC'}")
                
                with col2:
                    st.write("**Deal Terms**")
                    st.write(f"- Deal: {settlement['deal_description'] or 'N/A'}")
                    st.write(f"- Total Value: £{settlement['total_deal_value']:,.2f}")
                    st.write(f"- Artist Fee: £{settlement['artist_fee']:,.2f}")
                    st.write(f"- Booking Fee: £{settlement['booking_fee']:,.2f}")
                
                # Status indicators
                st.write("---")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    status_color = "🟢" if settlement['promoter_status'] == "PAID" else "🟡" if settlement['promoter_status'] == "PART PAID" else "🔴"
                    st.metric("Promoter Status", f"{status_color} {settlement['promoter_status']}")
                
                with col2:
                    status_color = "🟢" if settlement['artist_status'] == "SETTLED" else "🟡" if settlement['artist_status'] == "PARTIAL" else "🔴"
                    st.metric("Artist Status", f"{status_color} {settlement['artist_status']}")
                
                with col3:
                    st.metric("Overall", settlement['overall_status'])
            
            with tab2:
                # Money IN (from promoter)
                st.write("**Invoices Issued**")
                st.metric("Total Invoiced", f"£{settlement['total_invoiced']:,.2f}")
                
                if settlement['invoices']:
                    inv_df = pd.DataFrame(settlement['invoices'])
                    st.dataframe(
                        inv_df[['invoice_number', 'total_gross', 'is_paid']],
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No invoices for this show yet.")
                
                st.write("---")
                st.write("**Payments Received**")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Received", f"£{settlement['total_received']:,.2f}")
                with col2:
                    st.metric("Outstanding", f"£{settlement['outstanding_from_promoter']:,.2f}")
                with col3:
                    st.metric("Status", settlement['promoter_status'])
            
            with tab3:
                # Money OUT (payments made)
                st.write("**Outgoing Payments**")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Artist Payments", f"£{settlement['artist_payments']:,.2f}")
                with col2:
                    st.metric("Hotel", f"£{settlement['hotel_payments']:,.2f}")
                with col3:
                    st.metric("Flights", f"£{settlement['flight_payments']:,.2f}")
                with col4:
                    st.metric("Other", f"£{settlement['other_payments']:,.2f}")
                
                st.metric("Total Paid Out", f"£{settlement['total_paid_out']:,.2f}")
                
                if settlement['outgoing_payments']:
                    out_df = pd.DataFrame(settlement['outgoing_payments'])
                    st.dataframe(out_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No outgoing payments recorded yet.")
            
            with tab4:
                # Artist settlement
                st.write("**Artist Settlement Calculation**")
                
                st.write(f"Artist Fee: £{settlement['artist_fee']:,.2f}")
                
                if settlement['hotel_buyout'] > 0:
                    st.write(f"- Hotel Buyout: -£{settlement['hotel_buyout']:,.2f}")
                if settlement['flight_buyout'] > 0:
                    st.write(f"- Flight Buyout: -£{settlement['flight_buyout']:,.2f}")
                if settlement['withholding_tax'] > 0:
                    st.write(f"- Withholding Tax: -£{settlement['withholding_tax']:,.2f}")
                
                st.write("---")
                st.write(f"**Net Due to Artist: £{settlement['net_artist_due']:,.2f}**")
                st.write(f"Already Paid: £{settlement['artist_paid']:,.2f}")
                st.write(f"**Balance: £{settlement['artist_balance']:,.2f}**")
                
                # Status
                if settlement['artist_status'] == "SETTLED":
                    st.success("✅ Artist fully paid!")
                elif settlement['artist_status'] == "PARTIAL":
                    st.warning(f"🟡 Partial payment. £{settlement['artist_balance']:,.2f} remaining.")
                else:
                    st.error(f"🔴 Payment pending. £{settlement['artist_balance']:,.2f} due.")


# =============================================================================
# LEARNING NOTES: DATAFRAME DISPLAY
# =============================================================================
#
# st.dataframe():
#   Displays a pandas DataFrame as an interactive table.
#   
#   st.dataframe(df, use_container_width=True, hide_index=True)
#   
#   Options:
#   - use_container_width: Stretch to fill container
#   - hide_index: Don't show row numbers
#   - column_config: Customize how columns display
#
# COLUMN CONFIGURATION:
#   st.dataframe(df, column_config={
#       "amount": st.column_config.NumberColumn(
#           "Amount",
#           format="£%.2f"
#       ),
#       "date": st.column_config.DateColumn("Date"),
#       "status": st.column_config.SelectboxColumn("Status", options=["A", "B"])
#   })
#
# TABS:
#   tab1, tab2 = st.tabs(["Tab 1", "Tab 2"])
#   with tab1:
#       st.write("Content for tab 1")
#   with tab2:
#       st.write("Content for tab 2")
#
# =============================================================================


