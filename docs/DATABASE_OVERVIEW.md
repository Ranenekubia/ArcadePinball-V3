# Database Overview — Schema, Relationships & Integrity

This document is the single reference for the Arcade Pinball V3 database: **tables**, **relationships**, and **all logic that ensures data integrity**.

---

## 1. High-level model

**Central concept: the Show.** Every gig/performance is one row in `shows`. Other entities link to it via `show_id` or via `contract_number` (which is set on shows when contracts are imported).

```
                    ┌─────────────┐
                    │   SHOWS     │  ← Central hub (one row per gig)
                    │ show_id PK  │
                    │ contract_#  │
                    └──────┬──────┘
           ┌──────────────┼──────────────┬──────────────┬──────────────┐
           │              │              │              │              │
           ▼              ▼              ▼              ▼              ▼
    ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
    │ CONTRACTS  │ │ INVOICES   │ │ BANK_TX    │ │ OUTGOING   │ │ SETTLEMENTS│
    │ contract_# │ │ show_id FK │ │ show_id FK │ │ show_id FK │ │ show_id FK │
    │ show_id FK │ │ inv_number │ │ amount     │ │ bank_id FK │ │            │
    └────────────┘ └─────┬──────┘ └─────┬──────┘ └────────────┘ └────────────┘
                        │              │
                        │    ┌─────────┴─────────┐
                        │    │    HANDSHAKES     │  ← Bank ↔ Invoice matches
                        └────┤ bank_id FK        │
                             │ invoice_id FK     │
                             │ bank_amount_appl  │
                             └──────────────────┘
                        ┌────────────┐
                        │INVOICE_    │
                        │ITEMS       │  ← Line items per invoice
                        │invoice_id  │
                        └────────────┘
```

---

## 2. Schema — All tables and columns

### 2.1 `shows` (central hub)

| Column | Type | Constraints | Notes |
|--------|------|-------------|--------|
| show_id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique row ID |
| contract_number | TEXT | — | Links to contracts; used to attach invoices |
| agent | TEXT | — | Who booked the show |
| artist | TEXT | NOT NULL | Performer |
| event_name | TEXT | — | |
| venue | TEXT | — | |
| city | TEXT | — | |
| country | TEXT | — | |
| booking_date | TEXT | — | |
| performance_date | TEXT | — | |
| performance_day | TEXT | — | e.g. "Saturday" |
| deal_description | TEXT | — | e.g. "AF $3400 & BF $600" |
| total_deal_value | REAL | DEFAULT 0 | |
| currency | TEXT | DEFAULT 'GBP' | |
| artist_fee | REAL | DEFAULT 0 | |
| booking_fee | REAL | DEFAULT 0 | |
| hotel_buyout | REAL | DEFAULT 0 | |
| flight_buyout | REAL | DEFAULT 0 | |
| ground_transport_buyout | REAL | DEFAULT 0 | |
| withholding_tax | REAL | DEFAULT 0 | |
| net_artist_settlement | REAL | DEFAULT 0 | |
| promoter_name | TEXT | — | |
| promoter_email | TEXT | — | |
| promoter_phone | TEXT | — | |
| status | TEXT | DEFAULT 'Contracted' | |
| settlement_status | TEXT | DEFAULT 'Pending' | |
| notes | TEXT | — | |
| created_at | TEXT | — | |
| updated_at | TEXT | — | |

**Indexes:** `contract_number`, `artist`, `agent`, `performance_date`, `status`.

---

### 2.2 `contracts` (System One import)

| Column | Type | Constraints | Notes |
|--------|------|-------------|--------|
| contract_id | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| contract_number | TEXT | NOT NULL UNIQUE | Prevents duplicate contracts |
| booking_date | TEXT | — | |
| artist | TEXT | — | |
| event_name | TEXT | — | |
| venue | TEXT | — | |
| city | TEXT | — | |
| country | TEXT | — | |
| performance_date | TEXT | — | |
| performance_day | TEXT | — | |
| deal_description | TEXT | — | |
| total_deal_value | REAL | — | |
| currency | TEXT | DEFAULT 'GBP' | |
| artist_fee | REAL | — | |
| booking_fee | REAL | — | |
| booking_fee_vat | REAL | — | |
| hotel_buyout | REAL | DEFAULT 0 | |
| flight_buyout | REAL | DEFAULT 0 | |
| ground_transport_buyout | REAL | DEFAULT 0 | |
| withholding_tax | REAL | DEFAULT 0 | |
| withholding_tax_rate | REAL | — | |
| total_artist_settlement | REAL | — | |
| import_batch | TEXT | — | |
| imported_at | TEXT | — | |
| show_id | INTEGER | FK → shows(show_id) | Set when contract is linked to show |

**Integrity:** `contract_number` UNIQUE enforces one row per contract at DB level.  
**Indexes:** `contract_number`, `artist`.

---

### 2.3 `bank_transactions` (HSBC import — money in/out)

| Column | Type | Constraints | Notes |
|--------|------|-------------|--------|
| bank_id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique row ID |
| date | TEXT | NOT NULL | |
| type | TEXT | — | e.g. "CR" for credit |
| description | TEXT | NOT NULL | |
| paid_out | REAL | DEFAULT 0 | Money out |
| paid_in | REAL | DEFAULT 0 | Money in |
| amount | REAL | NOT NULL | Net (positive = in, negative = out) |
| currency | TEXT | NOT NULL DEFAULT 'GBP' | |
| transaction_hash | TEXT | — | Hash(date, amount, description) for deduplication |
| is_matched | INTEGER | DEFAULT 0 | 0 = not matched, 1 = has handshake(s) |
| show_id | INTEGER | FK → shows(show_id) | Optional |
| import_batch | TEXT | — | |
| imported_at | TEXT | — | |

**Integrity:** No UNIQUE on columns; duplicates are prevented in application by `transaction_hash`.  
**Indexes:** `date`, `transaction_hash`, `is_matched`.

---

### 2.4 `invoices`

| Column | Type | Constraints | Notes |
|--------|------|-------------|--------|
| invoice_id | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| invoice_number | TEXT | NOT NULL UNIQUE | Prevents duplicate invoices |
| contract_number | TEXT | — | Used to link to show at import |
| show_id | INTEGER | FK → shows(show_id) | Set when contract_number matches a show |
| from_entity | TEXT | — | |
| promoter_name | TEXT | — | |
| payment_bank_details | TEXT | — | |
| reference | TEXT | — | |
| currency | TEXT | NOT NULL DEFAULT 'GBP' | |
| total_net | REAL | DEFAULT 0 | |
| total_vat | REAL | DEFAULT 0 | |
| total_gross | REAL | NOT NULL | |
| invoice_date | TEXT | — | |
| show_date | TEXT | — | |
| is_paid | INTEGER | DEFAULT 0 | 0 = unpaid, 1 = paid |
| paid_amount | REAL | DEFAULT 0 | Sum of handshake amounts applied |
| balance_remaining | REAL | — | total_gross − paid_amount |
| import_batch | TEXT | — | |
| imported_at | TEXT | — | |

**Integrity:** `invoice_number` UNIQUE enforces one row per invoice.  
**Indexes:** `invoice_number`, `contract_number`, `show_id`.

---

### 2.5 `invoice_items` (line items per invoice)

| Column | Type | Constraints | Notes |
|--------|------|-------------|--------|
| item_id | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| invoice_id | INTEGER | NOT NULL, FK → invoices(invoice_id) | |
| account_code | TEXT | NOT NULL | e.g. "Booking Fee", "Artist Fee" |
| description | TEXT | — | |
| net | REAL | — | |
| vat | REAL | — | |
| gross | REAL | — | |

**Integrity:** FK ensures every line item belongs to an existing invoice.  
**Index:** `invoice_id`.

---

### 2.6 `outgoing_payments` (money out — artist, hotel, etc.)

| Column | Type | Constraints | Notes |
|--------|------|-------------|--------|
| payment_id | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| show_id | INTEGER | FK → shows(show_id) | Optional |
| payment_type | TEXT | NOT NULL | e.g. "Hotel", "Artist Advance" |
| description | TEXT | — | |
| amount | REAL | NOT NULL | |
| currency | TEXT | DEFAULT 'GBP' | |
| payment_date | TEXT | — | |
| payee | TEXT | — | |
| bank_reference | TEXT | — | |
| bank_id | INTEGER | FK → bank_transactions(bank_id) | Optional; links to debit row |
| notes | TEXT | — | |
| created_at | TEXT | — | |
| created_by | TEXT | — | |

**Integrity:** Both FKs enforced; `bank_id` links “money out” to a bank debit.  
**Indexes:** `show_id`, `payment_type`.

---

### 2.7 `handshakes` (bank payment ↔ invoice matches)

| Column | Type | Constraints | Notes |
|--------|------|-------------|--------|
| handshake_id | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| bank_id | INTEGER | NOT NULL, FK → bank_transactions(bank_id) | |
| invoice_id | INTEGER | NOT NULL, FK → invoices(invoice_id) | |
| bank_amount_applied | REAL | NOT NULL | Amount of this bank tx applied to this invoice |
| proxy_amount | REAL | DEFAULT 0 | Adjustments (FX, fees) |
| note | TEXT | — | |
| created_at | TEXT | — | |
| created_by | TEXT | — | |

**Integrity:** Both FKs enforced. One bank transaction can have multiple handshakes (one-to-many to invoices).  
**Indexes:** `bank_id`, `invoice_id`.

---

### 2.8 `settlements` (artist payment confirmation)

| Column | Type | Constraints | Notes |
|--------|------|-------------|--------|
| settlement_id | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| show_id | INTEGER | NOT NULL, FK → shows(show_id) | |
| artist | TEXT | NOT NULL | |
| amount_due | REAL | NOT NULL | |
| currency | TEXT | DEFAULT 'GBP' | |
| amount_paid | REAL | DEFAULT 0 | |
| balance | REAL | — | amount_due − amount_paid |
| status | TEXT | DEFAULT 'Pending' | Pending, Partial, Paid, Confirmed |
| payment_date | TEXT | — | |
| payment_reference | TEXT | — | |
| payment_method | TEXT | — | |
| confirmed_by | TEXT | — | |
| confirmed_at | TEXT | — | |
| artist_confirmed | INTEGER | DEFAULT 0 | |
| notes | TEXT | — | |
| created_at | TEXT | — | |
| updated_at | TEXT | — | |

**Integrity:** FK to `shows` enforced.  
**Indexes:** `show_id`, `status`.

---

## 3. Relationships (cardinality and FKs)

| From table | Column | To table | To column | Cardinality |
|------------|--------|----------|-----------|-------------|
| contracts | show_id | shows | show_id | N → 1 |
| bank_transactions | show_id | shows | show_id | N → 1 (optional) |
| invoices | show_id | shows | show_id | N → 1 (optional) |
| invoice_items | invoice_id | invoices | invoice_id | N → 1 |
| outgoing_payments | show_id | shows | show_id | N → 1 (optional) |
| outgoing_payments | bank_id | bank_transactions | bank_id | N → 1 (optional) |
| handshakes | bank_id | bank_transactions | bank_id | N → 1 |
| handshakes | invoice_id | invoices | invoice_id | N → 1 |
| settlements | show_id | shows | show_id | N → 1 |

**Logical links not stored as FK:**

- **Invoices → Shows:** Also matched by `contract_number`. At import, `invoice_importer` finds a show with the same `contract_number` (after stripping whitespace) and sets `invoices.show_id`.
- **Contracts → Shows:** Contract importer creates one show per contract and sets `contracts.show_id` and `shows.contract_number`.

---

## 4. Integrity — What the database and app enforce

### 4.1 Schema-level (SQLite)

- **Primary keys:** Every table has a single-column INTEGER PRIMARY KEY AUTOINCREMENT (unique row ID).
- **UNIQUE:**  
  - `contracts.contract_number`  
  - `invoices.invoice_number`  
  So duplicate contract numbers or invoice numbers cannot be inserted.
- **NOT NULL:** Used on critical fields (e.g. `shows.artist`, `invoices.invoice_number`, `invoices.total_gross`, `bank_transactions.date`, `description`, `amount`, etc.) so required values cannot be missing.
- **Foreign keys:** All FKs listed in Section 3 are declared in `database/schema.py`. SQLite will reject inserts/updates that reference non-existent parent rows **only if** foreign key enforcement is enabled.

### 4.2 Connection-level: foreign key enforcement

**File:** `database/connection.py`

- Every connection runs:  
  `PRAGMA foreign_keys = ON`
- So: inserts/updates that violate a foreign key (e.g. `handshakes.bank_id` pointing to a non-existent `bank_id`) are rejected by SQLite. This is the **main** mechanism that enforces referential integrity between tables.

### 4.3 Application-level duplicate detection (before insert)

Duplicates are avoided **before** insert so that UNIQUE constraints are not hit by accident and so we can return clear feedback (e.g. “duplicate skipped”).

| Entity | Uniqueness key | Where checked | How |
|--------|----------------|----------------|-----|
| Contracts | contract_number | `database/queries.py`: `check_contract_exists()` | Used in `create_contract()`; skip insert if exists |
| Invoices | invoice_number | `database/queries.py`: `check_invoice_exists()` | Used in `create_invoice()` and in `InvoiceImporter._insert_invoices()`; skip if exists |
| Bank transactions | (date, amount, description) | `database/queries.py`: `_generate_hash()`, `check_bank_transaction_exists()` | Hash stored in `transaction_hash`; `create_bank_transaction()` checks hash and skips if exists |

No UNIQUE index on `(date, amount, description)` or on `transaction_hash`; uniqueness for bank rows is enforced only in application logic using the hash.

### 4.4 Application-level linking (invoices and shows)

- **Contract import** (`importers/contract_importer.py`): For each contract row, creates one contract and one show; sets `shows.contract_number` and `contracts.show_id` so contract and show are linked.
- **Invoice import** (`importers/invoice_importer.py`): For each invoice, `_find_show_for_invoice()` looks up a show by `contract_number` (after `str(raw).strip()`). If found, sets `invoices.show_id`. So invoice–show integrity is kept by matching `contract_number` at import time.

### 4.5 Handshake lifecycle (consistency of matched state)

**Create handshake** (`database/queries.py`: `create_handshake()`):

1. Insert row into `handshakes` with `bank_id`, `invoice_id`, `bank_amount_applied`, `proxy_amount`.
2. Set `bank_transactions.is_matched = 1` for that `bank_id`.
3. Update `invoices`:  
   - `paid_amount += bank_amount_applied + proxy_amount`  
   - `balance_remaining = total_gross - paid_amount`  
   - `is_paid = 1` if `paid_amount >= total_gross`, else leave 0.

So: one transaction in the app creates the handshake and keeps bank “matched” and invoice “paid amount / balance / is_paid” in sync.

**Delete handshake** (`database/queries.py`: `delete_handshake()`):

1. Read handshake’s `bank_id`, `invoice_id`, `bank_amount_applied`, `proxy_amount`.
2. Delete the handshake row.
3. If no other handshakes exist for that `bank_id`, set `bank_transactions.is_matched = 0`.
4. Reverse invoice:  
   - `paid_amount -= (bank_amount_applied + proxy_amount)`  
   - Recompute `balance_remaining` and `is_paid`.

So: removing a handshake restores bank and invoice state consistently.

### 4.6 Type safety in critical paths

- In `create_handshake()`, `bank_id` and `invoice_id` are passed through `_safe_int()`, and amounts through `_safe_float()`, to avoid type errors from UI/DataFrames and to keep inserts predictable.

### 4.7 Settlement balance and status

- `create_settlement()` sets `balance = amount_due - amount_paid`.
- `update_settlement()` recalculates `balance` when `amount_due` or `amount_paid` changes, and sets `status` to `'Paid'` or `'Partial'` based on amounts. So settlement totals and status are kept consistent in application logic.

---

## 5. Indexes (performance and lookups)

Indexes are created in `database/schema.py` with `CREATE INDEX IF NOT EXISTS`:

- **shows:** contract_number, artist, agent, performance_date, status  
- **contracts:** contract_number, artist  
- **bank_transactions:** date, transaction_hash, is_matched  
- **invoices:** invoice_number, contract_number, show_id  
- **invoice_items:** invoice_id  
- **outgoing_payments:** show_id, payment_type  
- **handshakes:** bank_id, invoice_id  
- **settlements:** show_id, status  

These support filters (e.g. unpaid invoices, unmatched bank rows), joins (e.g. handshakes to bank and invoices), and duplicate checks (e.g. by contract_number, invoice_number, transaction_hash).

---

## 6. Summary

| Concern | Where it’s enforced |
|--------|--------------------|
| Unique row ID per table | PRIMARY KEY AUTOINCREMENT in schema |
| No duplicate contract numbers | UNIQUE on `contracts.contract_number` + `check_contract_exists()` before insert |
| No duplicate invoice numbers | UNIQUE on `invoices.invoice_number` + `check_invoice_exists()` before insert |
| No duplicate bank rows (same date/amount/desc) | `transaction_hash` + `check_bank_transaction_exists()` before insert |
| Referential integrity (all FKs) | `PRAGMA foreign_keys = ON` in `connection.py` |
| Invoices linked to shows | Import: match by `contract_number` (trimmed), set `invoices.show_id` |
| Contracts linked to shows | Import: one show per contract, set `contracts.show_id`, `shows.contract_number` |
| Handshake ↔ bank/invoice consistency | `create_handshake()` / `delete_handshake()` update bank_transactions and invoices in same transaction |
| Settlement balance/status | Recalculated in `create_settlement()` and `update_settlement()` |

This is the full picture of the database schema, relationships, and integrity logic for Arcade Pinball V3.
