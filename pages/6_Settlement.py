# =============================================================================
# pages/6_📊_Settlement.py
# =============================================================================
# PURPOSE:
#   Settlement Report - The full show settlement view.
#   Shows the complete financial picture for each show.
#
# THIS ADDRESSES YOUR REQUIREMENTS:
#   "We need full show settlement produced view and held in database"
#   "We need the team to be able to confirm when they have paid out 
#    what is due to the artist"
#
# FEATURES:
#   - Full settlement calculation per show
#   - Payment status tracking
#   - Team confirmation workflow
#   - Settlement email draft generation
#   - Export functionality
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
    load_settlements,
    create_settlement,
    update_settlement,
    confirm_settlement
)
from utils import calculate_show_settlement
from utils.styling import apply_minimal_style
from config import SETTLEMENT_STATUSES

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Settlement Report - Pinball V3",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply minimal styling
apply_minimal_style()

init_db()

# -----------------------------------------------------------------------------
# PAGE HEADER
# -----------------------------------------------------------------------------
st.title("Settlement Report")
st.caption("Full show settlement view with artist payment confirmation.")

# -----------------------------------------------------------------------------
# LOAD ALL DATA
# -----------------------------------------------------------------------------
shows_df = load_shows()
invoices_df = load_invoices()
handshakes_df = load_handshakes()
outgoing_df = load_outgoing_payments()
settlements_df = load_settlements()

# -----------------------------------------------------------------------------
# SHOW SELECTOR
# -----------------------------------------------------------------------------
if len(shows_df) == 0:
    st.info("No shows in the system. Import contracts to get started.")
    st.stop()

st.write("### Select Show")

show_options = {}
for _, row in shows_df.iterrows():
    artist = row['artist'] or 'Unknown'
    venue = row['venue'] or 'TBC'
    date = row['performance_date'] or 'TBC'
    status = row['settlement_status'] or 'Pending'
    
    # Add status emoji
    status_emoji = "✅" if status == "Confirmed" else "🟡" if status == "Paid" else "⚪"
    
    label = f"{status_emoji} #{row['show_id']} - {artist} @ {venue} ({date})"
    show_options[row['show_id']] = label

selected_show_id = st.selectbox(
    "Choose a show:",
    options=list(show_options.keys()),
    format_func=lambda x: show_options[x]
)

# -----------------------------------------------------------------------------
# CALCULATE SETTLEMENT
# -----------------------------------------------------------------------------
if selected_show_id:
    settlement = calculate_show_settlement(
        selected_show_id,
        shows_df,
        invoices_df,
        handshakes_df,
        outgoing_df
    )
    
    if not settlement:
        st.error("Could not calculate settlement for this show.")
        st.stop()
    
    st.write("---")
    
    # =========================================================================
    # SETTLEMENT OVERVIEW
    # =========================================================================
    st.write("### 📋 Settlement Overview")
    
    # Show info header
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write(f"**Artist:** {settlement['artist']}")
        st.write(f"**Event:** {settlement['event_name'] or 'N/A'}")
        st.write(f"**Venue:** {settlement['venue'] or 'N/A'}")
    
    with col2:
        st.write(f"**Contract:** {settlement['contract_number'] or 'N/A'}")
        st.write(f"**Date:** {settlement['performance_date'] or 'TBC'}")
        st.write(f"**Deal:** {settlement['deal_description'] or 'N/A'}")
    
    with col3:
        # Status badges
        st.write(f"**Promoter:** {settlement['promoter_status']}")
        st.write(f"**Artist:** {settlement['artist_status']}")
        st.write(f"**Overall:** {settlement['overall_status']}")
    
    st.write("---")
    
    # =========================================================================
    # FINANCIAL BREAKDOWN
    # =========================================================================
    st.write("### 💰 Financial Breakdown")
    
    col1, col2, col3 = st.columns(3)
    
    # Column 1: Money IN
    with col1:
        st.write("**💳 Money IN (from Promoter)**")
        st.metric("Total Invoiced", f"£{settlement['total_invoiced']:,.2f}")
        st.metric("Received", f"£{settlement['total_received']:,.2f}")
        st.metric(
            "Outstanding",
            f"£{settlement['outstanding_from_promoter']:,.2f}",
            delta=f"-£{settlement['outstanding_from_promoter']:,.2f}" if settlement['outstanding_from_promoter'] > 0 else None,
            delta_color="inverse"
        )
    
    # Column 2: Money OUT
    with col2:
        st.write("**💸 Money OUT (Paid by Agency)**")
        st.metric("Artist Payments", f"£{settlement['artist_payments']:,.2f}")
        st.metric("Hotel", f"£{settlement['hotel_payments']:,.2f}")
        st.metric("Flights + Other", f"£{settlement['flight_payments'] + settlement['other_payments']:,.2f}")
        st.metric("Total Paid Out", f"£{settlement['total_paid_out']:,.2f}")
    
    # Column 3: Artist Settlement
    with col3:
        st.write("**🎭 Artist Settlement**")
        st.write(f"Artist Fee: £{settlement['artist_fee']:,.2f}")
        
        deductions = settlement['hotel_buyout'] + settlement['flight_buyout'] + settlement['withholding_tax']
        if deductions > 0:
            st.write(f"Deductions: -£{deductions:,.2f}")
            st.caption(f"(Hotel: £{settlement['hotel_buyout']:,.2f}, "
                      f"Flights: £{settlement['flight_buyout']:,.2f}, "
                      f"WHT: £{settlement['withholding_tax']:,.2f})")
        
        st.metric("Net Due to Artist", f"£{settlement['net_artist_due']:,.2f}")
        st.metric("Already Paid", f"£{settlement['artist_paid']:,.2f}")
        st.metric(
            "Balance Due",
            f"£{settlement['artist_balance']:,.2f}",
            delta=f"-£{settlement['artist_balance']:,.2f}" if settlement['artist_balance'] > 0 else "✅ Settled",
            delta_color="inverse" if settlement['artist_balance'] > 0 else "off"
        )
    
    st.write("---")
    
    # =========================================================================
    # AGENCY POSITION
    # =========================================================================
    st.write("### 🏢 Agency Position")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Booking Fee Earned", f"£{settlement['booking_fee']:,.2f}")
    
    with col2:
        st.metric("Net Position", f"£{settlement['agency_position']:,.2f}")
    
    with col3:
        # Profitability indicator
        if settlement['agency_position'] > 0:
            st.success(f"✅ Positive: £{settlement['agency_position']:,.2f}")
        elif settlement['agency_position'] < 0:
            st.error(f"⚠️ Negative: £{settlement['agency_position']:,.2f}")
        else:
            st.info("Neutral position")
    
    st.write("---")
    
    # =========================================================================
    # PAYMENT CONFIRMATION
    # =========================================================================
    st.write("### ✅ Payment Confirmation")
    st.write("Use this section to confirm when artist has been paid.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Check if settlement record exists
        show_settlement = settlements_df[settlements_df['show_id'] == selected_show_id] if len(settlements_df) > 0 else pd.DataFrame()
        
        if len(show_settlement) > 0:
            current_settlement = show_settlement.iloc[0]
            status = current_settlement['status']
            
            # Display status
            if status in ['Settled', 'Confirmed']:
                st.success(f"**Status: ✅ SETTLED**")
                if current_settlement['confirmed_by']:
                    st.write(f"Settled by **{current_settlement['confirmed_by']}** on {current_settlement['confirmed_at'][:10] if current_settlement['confirmed_at'] else 'N/A'}")
            else:
                st.write(f"**Current Status:** {status}")
            
            # Only show confirm button if not yet settled
            if status not in ['Settled', 'Confirmed']:
                confirmer_name = st.text_input("Your Name", placeholder="Enter your name to confirm settlement")
                
                if st.button("✅ Mark as Settled", type="primary"):
                    if confirmer_name:
                        confirm_settlement(current_settlement['settlement_id'], confirmer_name)
                        st.success("✅ Show marked as SETTLED!")
                        st.rerun()
                    else:
                        st.error("Please enter your name.")
        else:
            st.info("No settlement record yet. Create one when ready to track payment.")
            
            if st.button("📝 Create Settlement Record"):
                settlement_data = {
                    'show_id': selected_show_id,
                    'artist': settlement['artist'],
                    'amount_due': settlement['net_artist_due'],
                    'currency': 'GBP',
                    'amount_paid': settlement['artist_paid'],
                    'status': 'Pending' if settlement['artist_balance'] > 0 else 'Paid'
                }
                result = create_settlement(settlement_data)
                if result:
                    st.success("✅ Settlement record created!")
                    st.rerun()
    
    with col2:
        st.write("**Quick Actions**")
        
        if st.button("📧 Generate Settlement Email", use_container_width=True):
            st.session_state['show_email'] = True
        
        if st.button("📥 Export Settlement PDF", use_container_width=True):
            st.info("PDF export coming soon!")
    
    # =========================================================================
    # SETTLEMENT EMAIL DRAFT
    # =========================================================================
    if st.session_state.get('show_email', False):
        st.write("---")
        st.write("### 📧 Settlement Email Draft")
        
        # Generate email template
        email_template = f"""Dear {settlement['artist']},

Hope the show went well at {settlement['venue'] or '[Venue]'}! 

Please see below the settlement for this show:

**Show Details:**
- Event: {settlement['event_name'] or 'N/A'}
- Date: {settlement['performance_date'] or 'TBC'}
- Venue: {settlement['venue'] or 'TBC'}

**Settlement Breakdown:**
- Artist Fee: £{settlement['artist_fee']:,.2f}"""
        
        if settlement['hotel_buyout'] > 0:
            email_template += f"\n- Hotel Buyout: -£{settlement['hotel_buyout']:,.2f}"
        if settlement['flight_buyout'] > 0:
            email_template += f"\n- Flight Buyout: -£{settlement['flight_buyout']:,.2f}"
        if settlement['withholding_tax'] > 0:
            email_template += f"\n- Withholding Tax: -£{settlement['withholding_tax']:,.2f}"
        
        email_template += f"""

**Net Settlement: £{settlement['net_artist_due']:,.2f}**

Payments Made:
- Amount Paid: £{settlement['artist_paid']:,.2f}
- Balance: £{settlement['artist_balance']:,.2f}

"""
        
        if settlement['artist_balance'] <= 0:
            email_template += "This show is now fully settled. Nothing more to pay.\n"
        else:
            email_template += f"Payment of £{settlement['artist_balance']:,.2f} will be made shortly.\n"
        
        email_template += """
Best regards,
Arcade Team
"""
        
        st.text_area(
            "Email Draft (copy and customize):",
            value=email_template,
            height=400
        )
        
        if st.button("Close Email"):
            st.session_state['show_email'] = False
            st.rerun()

# =============================================================================
# ALL SETTLEMENTS TABLE
# =============================================================================
st.write("---")
st.write("### 📋 All Settlements")
st.caption("Overview of all settlement records. Create settlements from individual show views above.")

if len(settlements_df) > 0:
    # Build display table with show info
    display_data = []
    for _, s in settlements_df.iterrows():
        # Get show info
        show_row = shows_df[shows_df['show_id'] == s['show_id']]
        if len(show_row) > 0:
            show = show_row.iloc[0]
            artist = show.get('artist', 'Unknown')
            venue = show.get('venue', '')
            perf_date = show.get('performance_date', '')
        else:
            artist = s.get('artist', 'Unknown')
            venue = ''
            perf_date = ''
        
        # Status emoji
        status = s.get('status', 'Pending')
        if status == 'Settled':
            status_display = '✅ Settled'
        elif status == 'Confirmed':
            status_display = '✅ Settled'  # Treat Confirmed as Settled for backwards compat
        elif status == 'Paid':
            status_display = '💰 Paid'
        elif status == 'Partial':
            status_display = '🟡 Partial'
        else:
            status_display = '⏳ Pending'
        
        display_data.append({
            'Artist': artist,
            'Venue': venue,
            'Date': perf_date,
            'Amount Due': f"£{s.get('amount_due', 0):,.2f}",
            'Amount Paid': f"£{s.get('amount_paid', 0):,.2f}",
            'Balance': f"£{s.get('balance', 0):,.2f}",
            'Status': status_display,
            'Confirmed By': s.get('confirmed_by', ''),
            'Confirmed At': s.get('confirmed_at', '')[:10] if s.get('confirmed_at') else '',
        })
    
    settlements_table = pd.DataFrame(display_data)
    st.dataframe(settlements_table, use_container_width=True, hide_index=True)
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Settlements", len(settlements_df))
    with col2:
        settled_count = len(settlements_df[settlements_df['status'].isin(['Settled', 'Confirmed'])])
        st.metric("Settled", settled_count)
    with col3:
        pending_count = len(settlements_df[settlements_df['status'].isin(['Pending', 'Partial', 'Paid'])])
        st.metric("Pending", pending_count)
    with col4:
        total_balance = settlements_df['balance'].sum() if 'balance' in settlements_df.columns else 0
        st.metric("Total Outstanding", f"£{total_balance:,.2f}")
else:
    st.info("No settlement records yet. Create settlements from individual show views above.")


# =============================================================================
# LEARNING NOTES: WORKFLOW PATTERNS
# =============================================================================
#
# CONFIRMATION WORKFLOW:
#   Many business processes need human confirmation.
#   Pattern:
#   1. Calculate/prepare data
#   2. Show preview to user
#   3. User reviews and confirms
#   4. Record who confirmed and when
#
# WHY TRACK CONFIRMATIONS?
#   - Audit trail: Know who approved what
#   - Accountability: Clear ownership
#   - Compliance: Some actions need sign-off
#   - Debugging: Trace back issues
#
# IMPLEMENTING IN STREAMLIT:
#   1. Store confirmation state in database
#   2. Show current status
#   3. Provide confirm button (with name input)
#   4. Update database with confirmer + timestamp
#   5. Refresh to show new status
#
# =============================================================================


