# =============================================================================
# pages/3_🔗_Match.py
# =============================================================================
# PURPOSE:
#   Match bank transactions to invoices (create "handshakes").
#   This is where reconciliation happens - linking payments to bills.
#
# HOW IT WORKS:
#   1. User selects ONE bank transaction (the payment received)
#   2. User selects ONE or MORE invoices (what the payment is for)
#   3. System calculates if amounts match
#   4. User can add proxy adjustments for FX/fees
#   5. User approves the match(es)
#
# ONE-TO-MANY MATCHING:
#   A single bank payment can pay multiple invoices.
#   Example: Promoter sends £5000 to pay Invoice A (£3000) and Invoice B (£2000)
#   
#   We create TWO handshakes:
#   - Bank £5000 → Invoice A: £3000 applied
#   - Bank £5000 → Invoice B: £2000 applied
# =============================================================================

import streamlit as st
import pandas as pd
from datetime import datetime
from database import (
    init_db,
    load_bank_transactions,
    load_invoices_with_show_details,
    load_handshakes,
    create_handshake
)
from utils.styling import apply_minimal_style

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Match Transactions - Pinball V3",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply minimal styling
apply_minimal_style()

init_db()

# -----------------------------------------------------------------------------
# PAGE HEADER
# -----------------------------------------------------------------------------
st.title("Match Transactions")
st.caption("Link bank payments to invoices. Select ONE payment and ONE or MORE invoices.")

# -----------------------------------------------------------------------------
# LOAD DATA
# -----------------------------------------------------------------------------
# Only show incoming payments (amount > 0); outgoing transactions have no invoices to match
bank_df = load_bank_transactions(incoming_only=True)
invoice_df = load_invoices_with_show_details()
handshake_df = load_handshakes()

# -----------------------------------------------------------------------------
# MATCHING SPACE: Only unmatched payments and unpaid invoices
# -----------------------------------------------------------------------------
# Matched items are not shown here; they appear in the Match table (handshakes) below.

if len(handshake_df) > 0:
    matched_bank_ids = set(handshake_df['bank_id'].unique())
    available_bank = bank_df[~bank_df['bank_id'].isin(matched_bank_ids)].copy()
else:
    matched_bank_ids = set()
    available_bank = bank_df.copy()

paid_invoice_ids = set(invoice_df[invoice_df['is_paid'] == 1]['invoice_id'].tolist()) if len(invoice_df) > 0 else set()
available_invoices = invoice_df[~invoice_df['invoice_id'].isin(paid_invoice_ids)].copy()

# -----------------------------------------------------------------------------
# THREE-COLUMN LAYOUT
# -----------------------------------------------------------------------------
col_bank, col_match, col_invoice = st.columns([2, 3, 2])

# -----------------------------------------------------------------------------
# LEFT COLUMN: BANK TRANSACTIONS (grouped by import / same system)
# -----------------------------------------------------------------------------
with col_bank:
    st.write("### Select Bank Payment")
    
    # Search filter
    bank_search = st.text_input(
        "Search bank transactions",
        key="bank_search",
        placeholder="Type to filter..."
    )
    
    # Apply search filter
    if bank_search:
        filtered_bank = available_bank[
            available_bank['description'].str.contains(bank_search, case=False, na=False)
        ].copy()
    else:
        filtered_bank = available_bank.copy()
    
    # Group key: same import_batch = same system; else group by date
    def _bank_group_key(row):
        batch = row.get('import_batch')
        if pd.notna(batch) and str(batch).strip():
            return str(batch).strip()
        return f"date_{row.get('date', '')}"
    
    filtered_bank['_group'] = filtered_bank.apply(_bank_group_key, axis=1)
    filtered_bank = filtered_bank.sort_values(['_group', 'date', 'bank_id'])
    bank_ids_ordered = filtered_bank['bank_id'].tolist()
    
    def _group_label(gkey, count):
        if gkey.startswith("date_"):
            d = gkey.replace("date_", "")
            return f"Same day ({d}) — {count} payment(s)"
        try:
            parts = gkey.replace("batch_", "").split("_")
            if len(parts) >= 1 and len(parts[0]) == 8:
                d = datetime.strptime(parts[0], "%Y%m%d").strftime("%d %b %Y")
                return f"Same statement ({d}) — {count} payment(s)"
        except Exception:
            pass
        return f"Same import — {count} payment(s)"
    
    group_counts = filtered_bank['_group'].value_counts()
    bank_options = {}
    prev_g = None
    for bid in bank_ids_ordered:
        row = filtered_bank[filtered_bank['bank_id'] == bid].iloc[0]
        g = row['_group']
        count = group_counts.get(g, 1)
        line = f"#{row['bank_id']} | {row['currency']} {row['amount']:,.2f} | {(row['description'] or '')[:40]}"
        if g != prev_g:
            header = _group_label(g, count)
            bank_options[bid] = f"▸ {header} · {line}"
        else:
            bank_options[bid] = f"    {line}"
        prev_g = g
    
    st.caption(f"Unmatched only: {len(filtered_bank)} payment(s)")
    
    if len(filtered_bank) > 0:
        selected_bank_id = st.radio(
            "Select a transaction:",
            options=bank_ids_ordered,
            format_func=lambda x: bank_options[x],
            key="bank_radio"
        )
        
        selected_bank = filtered_bank[filtered_bank['bank_id'] == selected_bank_id].iloc[0]
        st.success(f"Selected: **{selected_bank['currency']} {selected_bank['amount']:,.2f}**")
    else:
        if len(available_bank) == 0:
            st.info("No unmatched payments. Matched items are in the table below.")
        else:
            st.warning("No transactions match your search.")
        selected_bank = None

# -----------------------------------------------------------------------------
# RIGHT COLUMN: INVOICES
# -----------------------------------------------------------------------------
with col_invoice:
    st.write("### Select Invoice(s)")
    
    # Search filter
    inv_search = st.text_input(
        "Search invoices",
        key="inv_search",
        placeholder="Type to filter..."
    )
    
    # Apply search filter (include artist, event_name, venue)
    if inv_search:
        inv_search_lower = inv_search.lower()
        def matches_inv(row):
            for col in ['invoice_number', 'promoter_name', 'artist', 'event_name', 'venue']:
                val = row.get(col)
                if pd.notna(val) and inv_search_lower in str(val).lower():
                    return True
            return False
        filtered_inv = available_invoices[available_invoices.apply(matches_inv, axis=1)]
    else:
        filtered_inv = available_invoices
    
    st.caption(f"Unpaid only: {len(filtered_inv)} invoice(s)")
    
    # Multi-select for invoices
    selected_invoices = []
    
    if len(filtered_inv) > 0:
        # Create display labels: description/reference, promoter, invoice number, currency, amount
        # Prioritize the description (reference) since that's what users care about most
        inv_options = {}
        for _, row in filtered_inv.iterrows():
            # Description comes from reference field (set during invoice import)
            desc = row.get('reference') or ''
            if pd.isna(desc):
                desc = ''
            desc = str(desc).strip()[:35]
            
            # Get promoter/contact name
            promoter = row.get('promoter_name') or row.get('from_entity') or ''
            if pd.isna(promoter):
                promoter = ''
            promoter = str(promoter).strip()[:20]
            
            # Get artist from linked show (if available)
            artist = row.get('artist') or ''
            if pd.isna(artist):
                artist = ''
            artist = str(artist).strip()[:20]
            
            inv_num = row['invoice_number']
            curr = row['currency']
            amt = row['total_gross']
            
            # Build label: prioritize description, then artist or promoter
            parts = []
            if desc:
                parts.append(desc)
            if artist:
                parts.append(artist)
            elif promoter:
                parts.append(promoter)
            parts.append(inv_num)
            parts.append(f"{curr} {amt:,.2f}")
            
            label = " | ".join(parts)
            inv_options[row['invoice_id']] = label
        
        selected_inv_ids = st.multiselect(
            "Choose invoices:",
            options=list(inv_options.keys()),
            format_func=lambda x: inv_options[x],
            key="inv_multiselect"
        )
        
        # Get full rows for selected invoices
        for inv_id in selected_inv_ids:
            row = filtered_inv[filtered_inv['invoice_id'] == inv_id].iloc[0]
            selected_invoices.append(row)
        
        if selected_invoices:
            total_selected = sum(inv['total_gross'] for inv in selected_invoices)
            curr = selected_invoices[0]['currency']
            st.success(f"Selected {len(selected_invoices)} invoices: **{curr} {total_selected:,.2f}**")
            # Show detail for each selected invoice
            for inv in selected_invoices:
                desc = inv.get('reference') or ''
                if pd.isna(desc):
                    desc = ''
                desc = str(desc).strip()
                
                # Get artist or promoter
                artist = inv.get('artist') or ''
                if pd.isna(artist):
                    artist = ''
                promoter = inv.get('promoter_name') or ''
                if pd.isna(promoter):
                    promoter = ''
                
                who = artist if artist else promoter
                
                parts = []
                if desc:
                    parts.append(desc)
                if who:
                    parts.append(who)
                parts.append(f"{inv['currency']} {inv['total_gross']:,.2f}")
                
                st.caption(" · ".join(parts))
    else:
        if len(available_invoices) == 0:
            st.info("No unpaid invoices. Matched items are in the table below.")
        else:
            st.warning("No invoices match your search.")

# -----------------------------------------------------------------------------
# MIDDLE COLUMN: MATCHING LOGIC
# -----------------------------------------------------------------------------
with col_match:
    st.write("### Match & Approve")
    st.write("---")
    
    if selected_bank is not None and len(selected_invoices) > 0:
        # -----------------------------------------------------------------
        # CALCULATE TOTALS
        # -----------------------------------------------------------------
        bank_amount = float(selected_bank['amount'])
        bank_currency = selected_bank['currency']
        
        invoice_total = sum(float(inv['total_gross']) for inv in selected_invoices)
        inv_currency = selected_invoices[0]['currency']
        
        # -----------------------------------------------------------------
        # DISPLAY COMPARISON
        # -----------------------------------------------------------------
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.metric("Bank Payment", f"{bank_currency} {bank_amount:,.2f}")
        
        with col_b:
            st.metric(f"Invoices ({len(selected_invoices)})", f"{inv_currency} {invoice_total:,.2f}")
        
        # -----------------------------------------------------------------
        # CALCULATE DIFFERENCE
        # -----------------------------------------------------------------
        difference = invoice_total - bank_amount
        
        if abs(difference) < 0.01:
            st.success("**Perfect Match!** Amounts are equal.")
            match_status = "perfect"
        elif difference > 0:
            st.warning(f"**Short by {inv_currency} {difference:,.2f}**")
            st.caption("Invoice total is more than bank payment.")
            match_status = "short"
        else:
            st.info(f"**Over by {inv_currency} {abs(difference):,.2f}**")
            st.caption("Bank payment is more than invoice total.")
            match_status = "over"
        
        # -----------------------------------------------------------------
        # PROXY ADJUSTMENT
        # -----------------------------------------------------------------
        st.write("---")
        st.write("**Adjustments**")
        
        # Pre-fill proxy with the difference if not perfect match
        default_proxy = difference if abs(difference) > 0.01 else 0.0
        
        proxy_amount = st.number_input(
            "Proxy Adjustment",
            value=default_proxy,
            step=0.01,
            help="Use this to balance FX differences, fees, etc. Positive = we're owed more, Negative = we owe less"
        )
        
        # Note field
        note = st.text_input(
            "Note",
            placeholder="e.g., FX adjustment, split payment, etc.",
            help="Optional note explaining this match"
        )
        
        # -----------------------------------------------------------------
        # FINAL CALCULATION
        # -----------------------------------------------------------------
        final_balance = invoice_total - bank_amount - proxy_amount
        
        st.write("---")
        st.write("**Final Calculation**")
        st.write(f"Invoice Total: {inv_currency} {invoice_total:,.2f}")
        st.write(f"Bank Payment: {bank_currency} {bank_amount:,.2f}")
        if proxy_amount != 0:
            st.write(f"Proxy Adjustment: {inv_currency} {proxy_amount:,.2f}")
        st.write(f"**Balance: {inv_currency} {final_balance:,.2f}**")
        
        if abs(final_balance) < 0.01:
            st.success("Balanced")
        
        # -----------------------------------------------------------------
        # APPROVE BUTTON
        # -----------------------------------------------------------------
        st.write("---")
        
        if st.button("Approve Match(es)", type="primary", use_container_width=True):
            try:
                success_count = 0
                remaining_bank = bank_amount

                for idx, inv in enumerate(selected_invoices):
                    inv_id = int(inv['invoice_id'])
                    inv_amount = float(inv['total_gross'])
                    b_id = int(selected_bank['bank_id'])
                    amount_to_apply = min(remaining_bank, inv_amount)
                    this_proxy = proxy_amount if idx == 0 else 0.0

                    result = create_handshake(
                        bank_id=b_id,
                        invoice_id=inv_id,
                        bank_amount_applied=amount_to_apply,
                        proxy_amount=this_proxy,
                        note=note,
                        created_by="User"
                    )

                    if result:
                        success_count += 1
                        remaining_bank -= amount_to_apply

                st.balloons()
                st.success(f"Created {success_count} match(es) successfully")
                st.rerun()

            except Exception as e:
                st.error(f"Error creating matches: {str(e)}")
    
    else:
        # Show instructions if nothing selected
        st.info("Select a bank payment on the left and invoice(s) on the right")
        
        st.write("**How Matching Works:**")
        st.write("1. Select ONE bank payment (money received)")
        st.write("2. Select ONE or MORE invoices (what it pays for)")
        st.write("3. Review the amounts")
        st.write("4. Add proxy adjustment if needed")
        st.write("5. Click Approve to create the match")

# -----------------------------------------------------------------------------
# MATCH TABLE (Handshakes) — matched items shown below
# -----------------------------------------------------------------------------
st.write("---")
st.write("### Match table (Handshakes)")
st.caption("Once matched, payments and invoices move here. Full list on the Handshakes page.")
if len(handshake_df) > 0:
    # Show key columns for readability
    display_cols = ['bank_date', 'bank_desc', 'bank_amount', 'bank_currency', 'invoice_number', 'artist', 'event_name', 'bank_amount_applied', 'note', 'created_at']
    cols_present = [c for c in display_cols if c in handshake_df.columns]
    st.dataframe(handshake_df[cols_present] if cols_present else handshake_df, use_container_width=True, hide_index=True)
else:
    st.info("No matches yet. Create matches above.")

# =============================================================================
# LEARNING NOTES: SESSION STATE
# =============================================================================
#
# WHAT IS SESSION STATE?
#   Streamlit re-runs the entire script on every interaction.
#   Session state lets you persist data between runs.
#
# USAGE:
#   # Set a value
#   st.session_state['my_key'] = "my_value"
#   
#   # Get a value (with default)
#   value = st.session_state.get('my_key', 'default')
#   
#   # Check if exists
#   if 'my_key' in st.session_state:
#       ...
#
# COMMON USES:
#   - Store user selections
#   - Track multi-step workflows
#   - Cache expensive computations
#   - Implement confirmation dialogs
#
# WIDGET KEYS:
#   When you give a widget a key=, its value is automatically
#   stored in session_state:
#   
#   st.text_input("Name", key="user_name")
#   # Value is now in st.session_state['user_name']
#
# =============================================================================


