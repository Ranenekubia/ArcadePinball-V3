# =============================================================================
# pages/5_Outgoing.py
# =============================================================================
# PURPOSE:
#   Track outgoing payments - money going OUT from the agency.
#   Record from bank import (money out) or manual entry; view allocated vs all.
#
# FEATURES:
#   - Record payment FROM bank import (select money-out transaction, link show/type)
#   - Allocated money out: payments linked to a bank transaction
#   - Record payment (manual) for payments not yet in bank import
#   - Payment history with filters
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
from utils.styling import apply_minimal_style

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Outgoing Payments - Pinball V3",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

apply_minimal_style()
init_db()

# -----------------------------------------------------------------------------
# PAGE HEADER
# -----------------------------------------------------------------------------
st.title("Outgoing Payments")
st.caption("Record payments from bank (money out) or manually. View allocated and all payments.")

# -----------------------------------------------------------------------------
# LOAD DATA
# -----------------------------------------------------------------------------
shows_df = load_shows()
outgoing_df = load_outgoing_payments()
# Bank "money out" only (amount < 0) for selecting when recording from bank
bank_out_df = load_bank_transactions(outgoing_only=True)

# Which bank transactions are already linked to an outgoing payment
allocated_bank_ids = set()
if len(outgoing_df) > 0 and 'bank_id' in outgoing_df.columns:
    allocated_bank_ids = set(outgoing_df[outgoing_df['bank_id'].notna()]['bank_id'].dropna().astype(int))
unallocated_bank_out = bank_out_df[~bank_out_df['bank_id'].isin(allocated_bank_ids)].copy() if len(bank_out_df) > 0 else pd.DataFrame()
allocated_outgoing = outgoing_df[outgoing_df['bank_id'].notna()].copy() if len(outgoing_df) > 0 else pd.DataFrame()

# -----------------------------------------------------------------------------
# SECTION 1: RECORD PAYMENT FROM BANK (MONEY OUT)
# -----------------------------------------------------------------------------
st.write("---")
st.write("### 💸 Record payment from bank (money out)")
st.caption("Select a payment from your bank import (money out). It will be linked and categorised.")

if len(unallocated_bank_out) > 0:
    # Build options: bank_id -> label
    bank_options = {}
    for _, row in unallocated_bank_out.iterrows():
        bid = row['bank_id']
        amt = abs(float(row['amount']))
        curr = row.get('currency', 'GBP')
        desc = (row.get('description') or '')[:50]
        dt = row.get('date', '')
        bank_options[bid] = f"#{bid} | {dt} | {curr} {amt:,.2f} | {desc}"

    col_sel, col_meta = st.columns([2, 1])
    with col_sel:
        selected_bank_id = st.selectbox(
            "Select bank transaction (money out)",
            options=list(bank_options.keys()),
            format_func=lambda x: bank_options[x],
            key="bank_out_select"
        )
    with col_meta:
        st.caption(f"{len(unallocated_bank_out)} unallocated money-out transaction(s)")

    if selected_bank_id is not None:
        bank_row = unallocated_bank_out[unallocated_bank_out['bank_id'] == selected_bank_id].iloc[0]
        amount_from_bank = abs(float(bank_row['amount']))
        currency_from_bank = bank_row.get('currency') or 'GBP'
        date_from_bank = bank_row.get('date') or ''
        desc_from_bank = bank_row.get('description') or ''

        with st.form("allocate_bank_out_form"):
            # Show (optional)
            show_options = {None: "-- Optional: link to show --"}
            if len(shows_df) > 0:
                for _, row in shows_df.iterrows():
                    show_options[row['show_id']] = f"#{row['show_id']} - {row['artist']} @ {row['venue'] or 'TBC'}"
            selected_show = st.selectbox("Link to show", options=list(show_options.keys()), format_func=lambda x: show_options[x])
            payment_type = st.selectbox("Payment type", options=OUTGOING_PAYMENT_TYPES)
            payee = st.text_input("Payee", placeholder="e.g. Hotel, Artist name")
            notes = st.text_area("Notes (optional)", placeholder="Optional notes", height=60)
            submitted_alloc = st.form_submit_button("Save as outgoing payment")
            if submitted_alloc:
                payment_data = {
                    'show_id': selected_show,
                    'payment_type': payment_type,
                    'description': desc_from_bank,
                    'amount': amount_from_bank,
                    'currency': currency_from_bank,
                    'payment_date': date_from_bank,
                    'payee': payee or desc_from_bank[:50],
                    'bank_reference': None,
                    'bank_id': int(selected_bank_id),
                    'notes': notes,
                }
                result = create_outgoing_payment(payment_data)
                if result:
                    st.success("Payment recorded and linked to bank transaction.")
                    st.rerun()
                else:
                    st.error("Failed to save.")
else:
    st.info("No unallocated money-out transactions. Import bank data on the Import page; money-out rows will appear here.")

# -----------------------------------------------------------------------------
# SECTION 2: ALLOCATED MONEY OUT
# -----------------------------------------------------------------------------
st.write("---")
st.write("### ✅ Allocated money out")
st.caption("Payments that are linked to a bank transaction (from bank import).")

if len(allocated_outgoing) > 0:
    # Merge with bank for display (bank amount is negative; show absolute)
    if len(bank_out_df) > 0:
        bank_short = bank_out_df[['bank_id', 'date', 'description', 'amount', 'currency']].copy()
        bank_short.columns = ['bank_id', 'bank_date', 'bank_desc', 'bank_amount', 'bank_currency']
        bank_short['bank_amount'] = bank_short['bank_amount'].abs()
        merged = allocated_outgoing.merge(bank_short, on='bank_id', how='left')
    else:
        merged = allocated_outgoing.copy()
        merged['bank_date'] = merged['bank_desc'] = merged['bank_amount'] = merged['bank_currency'] = None
    display_cols = [c for c in ['payment_type', 'bank_date', 'bank_desc', 'bank_amount', 'bank_currency', 'payee', 'payment_date', 'show_id'] if c in merged.columns]
    st.dataframe(merged[display_cols], use_container_width=True, hide_index=True)
else:
    st.info("No allocated money-out payments yet. Record one from the section above.")

# -----------------------------------------------------------------------------
# SECTION 3: RECORD PAYMENT (MANUAL)
# -----------------------------------------------------------------------------
st.write("---")
st.write("### ➕ Record payment (manual)")
st.caption("For payments not yet in the bank import (e.g. pending, or different source).")

col_form, col_list = st.columns([1, 2])

with col_form:
    with st.form("new_payment_form"):
        if len(shows_df) > 0:
            show_options = {None: "-- Select a show --"}
            for _, row in shows_df.iterrows():
                show_options[row['show_id']] = f"#{row['show_id']} - {row['artist']} @ {row['venue'] or 'TBC'}"
            selected_show = st.selectbox("Link to show", options=list(show_options.keys()), format_func=lambda x: show_options[x])
        else:
            st.info("No shows. Import contracts first.")
            selected_show = None

        payment_type = st.selectbox("Payment type", options=OUTGOING_PAYMENT_TYPES)
        description = st.text_input("Description", placeholder="e.g. Hotel booking")
        col_a, col_b = st.columns([2, 1])
        with col_a:
            amount = st.number_input("Amount", min_value=0.0, step=0.01)
        with col_b:
            currency = st.selectbox("Currency", options=["GBP", "EUR", "USD", "AUD"])
        payment_date = st.date_input("Payment date", value=date.today())
        payee = st.text_input("Payee", placeholder="Who received the payment?")
        bank_reference = st.text_input("Bank reference (optional)", placeholder="e.g. TFR-12345")
        notes = st.text_area("Notes (optional)", height=60)
        submitted = st.form_submit_button("💾 Save payment (manual)")

        if submitted:
            if amount <= 0:
                st.error("Please enter a valid amount.")
            elif not payment_type:
                st.error("Please select a payment type.")
            else:
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
                    st.success("Payment recorded.")
                    st.rerun()
                else:
                    st.error("Failed to save.")

# -----------------------------------------------------------------------------
# SECTION 4: PAYMENT HISTORY (ALL)
# -----------------------------------------------------------------------------
with col_list:
    st.write("### 📋 Payment history")
    type_filter = st.selectbox("Filter by type", options=["All"] + OUTGOING_PAYMENT_TYPES, key="type_filter")
    show_filter_options = {"All": "All shows"}
    if len(shows_df) > 0:
        for _, row in shows_df.iterrows():
            show_filter_options[row['show_id']] = f"{row['artist']} @ {row['venue'] or 'TBC'}"
    show_filter = st.selectbox("Filter by show", options=list(show_filter_options.keys()), format_func=lambda x: show_filter_options[x], key="show_filter")
    filtered_df = outgoing_df.copy() if len(outgoing_df) > 0 else pd.DataFrame()
    if len(filtered_df) > 0:
        if type_filter != "All":
            filtered_df = filtered_df[filtered_df['payment_type'] == type_filter]
        if show_filter != "All":
            filtered_df = filtered_df[filtered_df['show_id'] == show_filter]
    if len(filtered_df) > 0:
        total_amount = filtered_df['amount'].sum()
        st.metric(f"Total ({len(filtered_df)} payments)", f"£{total_amount:,.2f}")
        type_totals = filtered_df.groupby('payment_type')['amount'].sum()
        for ptype, total in type_totals.items():
            st.caption(f"{ptype}: £{total:,.2f}")
        st.write("---")
        for _, row in filtered_df.iterrows():
            with st.container():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{row['payment_type']}** - {row['payee'] or 'Unknown'}")
                    st.write(f"£{row['amount']:,.2f} | {row['payment_date']}")
                    if row.get('description'):
                        st.caption(row['description'])
                    if pd.notna(row.get('bank_id')):
                        st.caption(f"Linked to bank #{int(row['bank_id'])}")
                with col2:
                    if row.get('show_id'):
                        st.caption(f"Show #{row['show_id']}")
                st.write("---")
    else:
        st.info("No outgoing payments yet.")
