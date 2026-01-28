# =============================================================================
# utils/calculations.py
# =============================================================================
# PURPOSE:
#   Contains calculation and business logic functions.
#   These determine things like:
#   - Is an invoice paid, partially paid, or unpaid?
#   - What's the total settlement for a show?
#   - What's the reconciliation status?
#
# WHY SEPARATE FROM DATABASE QUERIES?
#   - Queries are about GETTING data
#   - Calculations are about PROCESSING data
#   - Keeping them separate makes code cleaner and easier to test
#
# BUSINESS RULES:
#   These functions encode the business rules of your agency.
#   For example: "An invoice is PAID if applied_amount >= total_gross"
#   If the rules change, you only need to update these functions.
# =============================================================================

import pandas as pd
from config import AMOUNT_TOLERANCE


def calculate_payment_status(applied_amount, total_amount):
    """
    Calculate the payment status for an invoice or show.
    
    PARAMETERS:
        applied_amount (float): How much has been paid/applied
        total_amount (float): How much was due
    
    RETURNS:
        str: One of 'UNPAID', 'PART PAID', 'PAID', 'OVERPAID'
    
    BUSINESS RULES:
        - UNPAID: Nothing paid yet (applied ≈ 0)
        - PART PAID: Some paid but not all (0 < applied < total)
        - PAID: Fully paid (applied ≈ total)
        - OVERPAID: Paid too much (applied > total)
    
    WHY TOLERANCE?
        Floating point math can be imprecise:
        100.00 might be stored as 99.99999999
        We use a tolerance (0.01) to handle this.
    
    EXAMPLE:
        calculate_payment_status(0, 1000)      → 'UNPAID'
        calculate_payment_status(500, 1000)    → 'PART PAID'
        calculate_payment_status(1000, 1000)   → 'PAID'
        calculate_payment_status(1100, 1000)   → 'OVERPAID'
    """
    # Handle None values
    applied_amount = applied_amount or 0
    total_amount = total_amount or 0
    
    # UNPAID: Nothing applied (within tolerance of zero)
    if abs(applied_amount) < AMOUNT_TOLERANCE:
        return "UNPAID"
    
    # PART PAID: Some applied but less than total
    elif applied_amount + AMOUNT_TOLERANCE < total_amount:
        return "PART PAID"
    
    # PAID: Applied equals total (within tolerance)
    elif abs(applied_amount - total_amount) <= AMOUNT_TOLERANCE:
        return "PAID"
    
    # OVERPAID: Applied more than total
    else:
        return "OVERPAID"


def calculate_invoice_status(invoice_df, handshake_df):
    """
    Calculate payment status for each invoice.
    
    PARAMETERS:
        invoice_df (pd.DataFrame): All invoices
        handshake_df (pd.DataFrame): All handshakes (payment matches)
    
    RETURNS:
        pd.DataFrame: Invoices with added columns:
            - paid_amount: Total amount paid
            - balance: Amount still owed
            - status: UNPAID/PART PAID/PAID/OVERPAID
    
    HOW IT WORKS:
        1. Start with all invoices
        2. For each invoice, sum up all handshakes (payments applied)
        3. Calculate balance = total - paid
        4. Determine status based on paid vs total
    """
    if len(invoice_df) == 0:
        return pd.DataFrame()
    
    # Copy to avoid modifying original
    result = invoice_df.copy()
    
    # Initialize columns
    result['paid_amount'] = 0.0
    result['proxy_amount'] = 0.0
    
    # Sum handshakes per invoice
    if len(handshake_df) > 0:
        for invoice_id in result['invoice_id']:
            # Find all handshakes for this invoice
            matches = handshake_df[handshake_df['invoice_id'] == invoice_id]
            
            if len(matches) > 0:
                # Sum the amounts
                paid = matches['bank_amount_applied'].sum()
                proxy = matches['proxy_amount'].sum()
                
                # Update the result DataFrame
                result.loc[result['invoice_id'] == invoice_id, 'paid_amount'] = paid
                result.loc[result['invoice_id'] == invoice_id, 'proxy_amount'] = proxy
    
    # Calculate derived columns
    result['total_applied'] = result['paid_amount'] + result['proxy_amount']
    result['balance'] = result['total_gross'] - result['total_applied']
    
    # Calculate status for each row
    result['status'] = result.apply(
        lambda row: calculate_payment_status(row['total_applied'], row['total_gross']),
        axis=1
    )
    
    return result


def calculate_show_settlement(show_id, show_df, invoice_df, handshake_df, outgoing_df):
    """
    Calculate the full settlement picture for a single show.
    
    PARAMETERS:
        show_id (int): The show to calculate for
        show_df (pd.DataFrame): Shows data
        invoice_df (pd.DataFrame): Invoices data
        handshake_df (pd.DataFrame): Handshakes data
        outgoing_df (pd.DataFrame): Outgoing payments data
    
    RETURNS:
        dict: Complete settlement breakdown including:
            - Show details
            - Money IN (invoices, payments received)
            - Money OUT (artist payments, expenses)
            - Net position
            - Status
    
    THIS IS THE "FULL SHOW SETTLEMENT VIEW" FROM YOUR REQUIREMENTS.
    It shows everything about a show's financial position.
    """
    # Get show details
    show = show_df[show_df['show_id'] == show_id]
    if len(show) == 0:
        return None
    show = show.iloc[0]
    
    # -----------------------------------------------------------------
    # MONEY IN: What we've invoiced and received
    # -----------------------------------------------------------------
    
    # Get invoices for this show
    show_invoices = invoice_df[invoice_df['show_id'] == show_id]
    
    # Calculate invoice totals
    total_invoiced = show_invoices['total_gross'].sum() if len(show_invoices) > 0 else 0
    
    # Get handshakes (payments) for these invoices
    if len(show_invoices) > 0 and len(handshake_df) > 0:
        invoice_ids = show_invoices['invoice_id'].tolist()
        show_handshakes = handshake_df[handshake_df['invoice_id'].isin(invoice_ids)]
        total_received = show_handshakes['bank_amount_applied'].sum() + show_handshakes['proxy_amount'].sum()
    else:
        total_received = 0
    
    # Calculate outstanding
    outstanding_from_promoter = total_invoiced - total_received
    
    # -----------------------------------------------------------------
    # MONEY OUT: What we've paid out
    # -----------------------------------------------------------------
    
    # Get outgoing payments for this show
    show_outgoing = outgoing_df[outgoing_df['show_id'] == show_id] if len(outgoing_df) > 0 else pd.DataFrame()
    
    # Break down by type
    artist_payments = 0
    hotel_payments = 0
    flight_payments = 0
    other_payments = 0
    
    if len(show_outgoing) > 0:
        for _, payment in show_outgoing.iterrows():
            ptype = payment.get('payment_type', '')
            amount = payment.get('amount', 0) or 0
            
            if 'artist' in ptype.lower():
                artist_payments += amount
            elif 'hotel' in ptype.lower():
                hotel_payments += amount
            elif 'flight' in ptype.lower():
                flight_payments += amount
            else:
                other_payments += amount
    
    total_paid_out = artist_payments + hotel_payments + flight_payments + other_payments
    
    # -----------------------------------------------------------------
    # ARTIST SETTLEMENT
    # -----------------------------------------------------------------
    
    # What the artist should receive (from show/contract)
    artist_fee_due = show.get('artist_fee', 0) or 0
    
    # Deductions
    hotel_buyout = show.get('hotel_buyout', 0) or 0
    flight_buyout = show.get('flight_buyout', 0) or 0
    withholding_tax = show.get('withholding_tax', 0) or 0
    
    # Net to artist
    net_artist_due = artist_fee_due - hotel_buyout - flight_buyout - withholding_tax
    
    # What's been paid to artist
    artist_paid = artist_payments
    
    # Artist balance
    artist_balance = net_artist_due - artist_paid
    
    # -----------------------------------------------------------------
    # AGENCY POSITION
    # -----------------------------------------------------------------
    
    # Booking fee earned
    booking_fee = show.get('booking_fee', 0) or 0
    
    # Net agency position = received - paid out
    agency_position = total_received - total_paid_out
    
    # -----------------------------------------------------------------
    # OVERALL STATUS
    # -----------------------------------------------------------------
    
    # Promoter status
    if outstanding_from_promoter <= AMOUNT_TOLERANCE:
        promoter_status = "PAID"
    elif total_received > AMOUNT_TOLERANCE:
        promoter_status = "PART PAID"
    else:
        promoter_status = "UNPAID"
    
    # Artist status
    if artist_balance <= AMOUNT_TOLERANCE:
        artist_status = "SETTLED"
    elif artist_paid > AMOUNT_TOLERANCE:
        artist_status = "PARTIAL"
    else:
        artist_status = "PENDING"
    
    # Overall show status
    if promoter_status == "PAID" and artist_status == "SETTLED":
        overall_status = "COMPLETE"
    elif promoter_status == "PAID" and artist_status != "SETTLED":
        overall_status = "AWAITING ARTIST PAYMENT"
    elif promoter_status != "PAID":
        overall_status = "AWAITING PROMOTER PAYMENT"
    else:
        overall_status = "IN PROGRESS"
    
    # -----------------------------------------------------------------
    # BUILD RESULT
    # -----------------------------------------------------------------
    
    return {
        # Show info
        'show_id': show_id,
        'contract_number': show.get('contract_number'),
        'artist': show.get('artist'),
        'event_name': show.get('event_name'),
        'venue': show.get('venue'),
        'performance_date': show.get('performance_date'),
        
        # Deal terms
        'deal_description': show.get('deal_description'),
        'total_deal_value': show.get('total_deal_value', 0),
        'artist_fee': artist_fee_due,
        'booking_fee': booking_fee,
        
        # Deductions
        'hotel_buyout': hotel_buyout,
        'flight_buyout': flight_buyout,
        'withholding_tax': withholding_tax,
        
        # Money IN
        'total_invoiced': total_invoiced,
        'total_received': total_received,
        'outstanding_from_promoter': outstanding_from_promoter,
        'promoter_status': promoter_status,
        
        # Money OUT
        'artist_payments': artist_payments,
        'hotel_payments': hotel_payments,
        'flight_payments': flight_payments,
        'other_payments': other_payments,
        'total_paid_out': total_paid_out,
        
        # Artist settlement
        'net_artist_due': net_artist_due,
        'artist_paid': artist_paid,
        'artist_balance': artist_balance,
        'artist_status': artist_status,
        
        # Agency
        'agency_position': agency_position,
        
        # Status
        'overall_status': overall_status,
        
        # Invoice details
        'invoices': show_invoices.to_dict('records') if len(show_invoices) > 0 else [],
        
        # Payment details
        'outgoing_payments': show_outgoing.to_dict('records') if len(show_outgoing) > 0 else [],
    }


def calculate_reconciliation_summary(invoice_df, handshake_df):
    """
    Calculate reconciliation summary for all invoices.
    This is a simpler version that just shows invoice payment status.
    
    PARAMETERS:
        invoice_df (pd.DataFrame): All invoices
        handshake_df (pd.DataFrame): All handshakes
    
    RETURNS:
        pd.DataFrame: Summary with status per invoice
    """
    return calculate_invoice_status(invoice_df, handshake_df)


# =============================================================================
# LEARNING NOTES: BUSINESS LOGIC
# =============================================================================
#
# WHAT IS BUSINESS LOGIC?
#   Business logic is the code that implements the rules of your business.
#   It's not about how data is stored or displayed - it's about what
#   the data MEANS and how decisions are made.
#
# EXAMPLES OF BUSINESS LOGIC:
#   - "An invoice is PAID when the full amount has been received"
#   - "Artist settlement = Artist Fee - Buyouts - Tax"
#   - "Show is COMPLETE when promoter paid and artist settled"
#
# WHY KEEP IT SEPARATE?
#   1. Easy to change: Business rules change often
#   2. Easy to test: Can test rules without database
#   3. Easy to understand: All rules in one place
#   4. Reusable: Same rules used in UI, reports, etc.
#
# TIPS FOR BUSINESS LOGIC:
#   - Use clear function names that describe the rule
#   - Document the rule in comments
#   - Handle edge cases (None values, zero amounts)
#   - Use constants for magic numbers (like AMOUNT_TOLERANCE)
#
# =============================================================================


