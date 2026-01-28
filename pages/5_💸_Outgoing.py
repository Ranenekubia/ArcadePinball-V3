# =============================================================================
# pages/5_💸_Outgoing.py
# =============================================================================
# PURPOSE:
#   Track outgoing payments - money going OUT from the agency.
#   This includes: artist payments, hotel bookings, flights, expenses.
#
# THIS ADDRESSES YOUR REQUIREMENT:
#   "We also need reconcile outgoing payments with the show - 
#    so for example a hotel..."
#
# FEATURES:
#   - Record new outgoing payments
#   - Link payments to shows
#   - Categorize by type (Artist, Hotel, Flight, etc.)
#   - View payment history
# =============================================================================

import streamlit as st
import pandas as pd
from datetime import datetime, date
from database import (
    init_db,
    load_shows,
    load_outgoing_payments,
    create_outgoing_payment,
    load_bank_transactions
)
from config import OUTGOING_PAYMENT_TYPES

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Outgoing Payments - Pinball V3",
    page_icon="💸",
    layout="wide"
)

init_db()

# -----------------------------------------------------------------------------
# PAGE HEADER
# -----------------------------------------------------------------------------
st.title("💸 Outgoing Payments")
st.caption("Track payments made by the agency: artist fees, hotels, flights, expenses.")

# -----------------------------------------------------------------------------
# LOAD DATA
# -----------------------------------------------------------------------------
shows_df = load_shows()
outgoing_df = load_outgoing_payments()
bank_df = load_bank_transactions()

# -----------------------------------------------------------------------------
# TWO-COLUMN LAYOUT
# -----------------------------------------------------------------------------
col_form, col_list = st.columns([1, 2])

# -----------------------------------------------------------------------------
# LEFT COLUMN: ADD NEW PAYMENT
# -----------------------------------------------------------------------------
with col_form:
    st.write("### ➕ Record Payment")
    
    with st.form("new_payment_form"):
        # Show selection
        if len(shows_df) > 0:
            show_options = {
                None: "-- Select a show --"
            }
            for _, row in shows_df.iterrows():
                label = f"#{row['show_id']} - {row['artist']} @ {row['venue'] or 'TBC'}"
                show_options[row['show_id']] = label
            
            selected_show = st.selectbox(
                "Link to Show",
                options=list(show_options.keys()),
                format_func=lambda x: show_options[x],
                help="Which show is this payment for?"
            )
        else:
            st.info("No shows in system. Import contracts first.")
            selected_show = None
        
        # Payment type
        payment_type = st.selectbox(
            "Payment Type",
            options=OUTGOING_PAYMENT_TYPES,
            help="What kind of payment is this?"
        )
        
        # Description
        description = st.text_input(
            "Description",
            placeholder="e.g., Hotel booking for 2 nights",
            help="Brief description of the payment"
        )
        
        # Amount
        col_a, col_b = st.columns([2, 1])
        with col_a:
            amount = st.number_input(
                "Amount",
                min_value=0.0,
                step=0.01,
                help="Payment amount"
            )
        with col_b:
            currency = st.selectbox(
                "Currency",
                options=["GBP", "EUR", "USD", "AUD"]
            )
        
        # Date
        payment_date = st.date_input(
            "Payment Date",
            value=date.today(),
            help="When was/will this be paid?"
        )
        
        # Payee
        payee = st.text_input(
            "Payee",
            placeholder="e.g., Marriott Hotel, Artist Name",
            help="Who received the payment?"
        )
        
        # Bank reference (optional)
        bank_reference = st.text_input(
            "Bank Reference (optional)",
            placeholder="e.g., TFR-12345",
            help="Reference from bank statement"
        )
        
        # Notes
        notes = st.text_area(
            "Notes (optional)",
            placeholder="Any additional notes...",
            height=80
        )
        
        # Submit button
        submitted = st.form_submit_button(
            "💾 Save Payment",
            type="primary",
            use_container_width=True
        )
        
        if submitted:
            if amount <= 0:
                st.error("Please enter a valid amount.")
            elif not payment_type:
                st.error("Please select a payment type.")
            else:
                # Create the payment record
                payment_data = {
                    'show_id': selected_show,
                    'payment_type': payment_type,
                    'description': description,
                    'amount': amount,
                    'currency': currency,
                    'payment_date': payment_date.isoformat(),
                    'payee': payee,
                    'bank_reference': bank_reference,
                    'notes': notes,
                }
                
                result = create_outgoing_payment(payment_data)
                
                if result:
                    st.success("✅ Payment recorded!")
                    st.rerun()
                else:
                    st.error("❌ Failed to save payment.")

# -----------------------------------------------------------------------------
# RIGHT COLUMN: PAYMENT LIST
# -----------------------------------------------------------------------------
with col_list:
    st.write("### 📋 Payment History")
    
    # Filters
    col_a, col_b = st.columns(2)
    
    with col_a:
        type_filter = st.selectbox(
            "Filter by Type",
            options=["All"] + OUTGOING_PAYMENT_TYPES
        )
    
    with col_b:
        # Show filter
        if len(shows_df) > 0:
            show_filter_options = {"All": "All Shows"}
            for _, row in shows_df.iterrows():
                show_filter_options[row['show_id']] = f"{row['artist']} @ {row['venue'] or 'TBC'}"
            
            show_filter = st.selectbox(
                "Filter by Show",
                options=list(show_filter_options.keys()),
                format_func=lambda x: show_filter_options[x]
            )
        else:
            show_filter = "All"
    
    # Apply filters
    filtered_df = outgoing_df.copy() if len(outgoing_df) > 0 else pd.DataFrame()
    
    if len(filtered_df) > 0:
        if type_filter != "All":
            filtered_df = filtered_df[filtered_df['payment_type'] == type_filter]
        
        if show_filter != "All":
            filtered_df = filtered_df[filtered_df['show_id'] == show_filter]
    
    # Display
    if len(filtered_df) > 0:
        # Summary stats
        total_amount = filtered_df['amount'].sum()
        st.metric(
            f"Total ({len(filtered_df)} payments)",
            f"£{total_amount:,.2f}"
        )
        
        # Breakdown by type
        st.write("**By Type:**")
        type_totals = filtered_df.groupby('payment_type')['amount'].sum()
        for ptype, total in type_totals.items():
            st.write(f"- {ptype}: £{total:,.2f}")
        
        st.write("---")
        
        # Payment list
        for _, row in filtered_df.iterrows():
            with st.container():
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    st.write(f"**{row['payment_type']}** - {row['payee'] or 'Unknown'}")
                    st.write(f"£{row['amount']:,.2f} | {row['payment_date']}")
                    if row['description']:
                        st.caption(row['description'])
                
                with col2:
                    if row['show_id']:
                        st.caption(f"Show #{row['show_id']}")
                
                st.write("---")
    else:
        st.info("No outgoing payments recorded yet.")
        st.write("Use the form on the left to record a payment.")


# =============================================================================
# LEARNING NOTES: FORMS IN STREAMLIT
# =============================================================================
#
# WHY USE FORMS?
#   Normally, Streamlit re-runs the script on EVERY widget interaction.
#   Forms batch multiple inputs and only submit when you click the button.
#   This is better for data entry - user fills everything, then submits.
#
# FORM SYNTAX:
#   with st.form("unique_form_key"):
#       name = st.text_input("Name")
#       age = st.number_input("Age")
#       
#       submitted = st.form_submit_button("Submit")
#       
#       if submitted:
#           # Process the form data
#           st.write(f"Hello {name}, you are {age}")
#
# FORM RULES:
#   - Every form needs a unique key
#   - Must have exactly one submit button
#   - Widgets inside form don't trigger reruns
#   - Only submit button triggers rerun
#   - Can't have buttons (other than submit) inside forms
#
# =============================================================================


