# Arcade Pinball V3 — Platform Documentation

**Flows · Logic · Reasoning**

This document describes how every page works, the logic behind decisions, and how to keep it updated when the platform changes.

---

## 1. Platform overview

**What it is:** A Streamlit app for talent agency show reconciliation — bookings, invoices, bank payments, and settlements.

**Core idea:** The **show** is the anchor. Contracts, invoices, bank payments, outgoing payments, and settlements all link to a show. Reconciliation = matching money received (bank) to money billed (invoices) via **handshakes**.

**Entry point:** `app.py` sets page config, injects the collapsed sidebar, then redirects to the Dashboard (`pages/1_Dashboard.py`). Users never stay on `app.py`.

**Navigation:** Collapsed icon sidebar (`utils/sidebar_nav.py`). Buttons set a session-state target; on the next run, `inject_sidebar_collapsed()` calls `st.switch_page()` at top level (callbacks cannot call `st.switch_page()`). Pages use ASCII filenames for reliable routing.

---

## 2. Data model and reasoning

| Table | Role |
|-------|------|
| **shows** | One row per gig/performance. Central hub; other tables link via `show_id` or `contract_number`. |
| **contracts** | Deal terms from System One. Each contract creates one show; linked by `contract_number`. |
| **invoices** | Bills sent to promoters. Link to show via `contract_number` (matched at import) or `show_id`. |
| **invoice_items** | Line items per invoice (Booking Fee, Artist Fee, etc.). |
| **bank_transactions** | Money in (credits) and out (debits). Only **incoming** (amount > 0) are used for matching. |
| **handshakes** | Links one bank payment to one or more invoices; records amount applied and optional proxy. |
| **outgoing_payments** | Money paid out (artist, hotel, flight, etc.); linked to show. |
| **settlements** | Artist payment tracking and team confirmation. |

**Why contract_number?** Invoices and shows both get a contract number. Matching at import (and on Match) uses it so “this payment is for this show’s invoice” is unambiguous.

**Why handshakes?** One bank payment can pay several invoices (e.g. one transfer for two events). Handshakes record how much of that payment applies to each invoice.

**Full database reference:** For the complete schema (all columns and types), relationships (FKs and cardinality), and **all integrity logic** (constraints, duplicate detection, handshake lifecycle, linking), see **[docs/DATABASE_OVERVIEW.md](DATABASE_OVERVIEW.md)**.

---

## 3. App entry and sidebar

### app.py

- **Flow:** Run → `st.set_page_config()` → `inject_sidebar_collapsed()` → `st.switch_page("pages/1_Dashboard.py")`.
- **Logic:** Dashboard is the intended home; no content is rendered on the root app URL.
- **Reasoning:** Single place for config and nav; users always land on Dashboard.

### utils/sidebar_nav.py

- **Flow:** Each nav button has `on_click=_go` with page path. `_go(path)` sets `st.session_state["nav_target"] = path`. On the next run, `inject_sidebar_collapsed()` pops `nav_target` and, if set, calls `st.switch_page(target)` at top level.
- **Logic:** No `st.switch_page()` or `st.rerun()` inside callbacks (Streamlit no-op). Session state defers the switch to top level.
- **Reasoning:** Avoids “Calling st.rerun() within a callback is a no-op” and keeps nav working.

---

## 4. Page-by-page documentation

### 4.1 Dashboard — `pages/1_Dashboard.py`

**Purpose:** One-screen overview: counts, payment status, what needs attention.

**Flow:**
1. `init_db()` (safe, idempotent).
2. Load shows, invoices, bank, handshakes, settlements, outgoing.
3. Quick stats row (counts for shows, invoices, bank, handshakes, settlements).
4. Payment status (e.g. paid vs unpaid invoices).
5. Action items / recent activity if implemented.
6. Quick action buttons to Import, Match, etc.

**Logic:**
- All metrics from current DB state; no caching in the doc (caching can be added later).
- Counts and status derived from the same load_* functions used elsewhere.

**Reasoning:** Answer “Is everything okay?” and “What needs my attention?” without opening other pages.

---

### 4.2 Import — `pages/2_Import.py`

**Purpose:** Bring external data in: bank CSV, contract CSV/Excel, invoice CSV. Show current data and optional clear.

**Flow:**
1. **Bank:** Upload CSV → “Import Bank Transactions” → `BankImporter` reads, dedupes by hash(date, amount, description), inserts new rows.
2. **Contracts:** Upload CSV/Excel → “Import Contracts” → `ContractImporter` maps columns, dedupes by contract_number, inserts contract + **creates one show per contract** (same contract_number).
3. **Invoices:** Upload CSV → “Import Invoices” → `InvoiceImporter` groups by invoice number, dedupes by invoice number, **links to show by contract_number** (strip whitespace), inserts invoice + invoice_items.
4. **Current data:** Four expanders (Bank, Contracts, Invoices, Shows) show **full schema** (all columns), up to 50 rows. “View full screen” sets session state; on next run only that table is shown (native `st.dataframe`) with “Exit” to clear and return.
5. **Data management:** Clear buttons with two-click confirm; clear order respects foreign keys (e.g. handshakes before invoices).

**Logic:**
- Duplicate detection: bank = hash; contracts = contract_number; invoices = invoice_number.
- Invoices attach to show only when contract_number matches a show (from contract import). Contract number normalized (strip) for matching.
- Full-screen view: session-state key; when set, render only that table + Exit, then `st.stop()` so the rest of the page is not rendered.

**Reasoning:** One place for all ingestion; full columns so users see exactly what’s stored; full-screen for large tables; safe clear with confirmation.

---

### 4.3 Match — `pages/3_Match.py`

**Purpose:** Reconcile bank payments to invoices (create handshakes). Only unmatched payments and unpaid invoices in the selection area; matched pairs shown in the table below.

**Flow:**
1. Load incoming-only bank (`load_bank_transactions(incoming_only=True)`), all invoices with show details, all handshakes.
2. **Matching space:** `available_bank` = bank rows not in any handshake; `available_invoices` = invoices not fully paid. Only these appear in the left/right selection.
3. Left: Bank payments grouped by import_batch or date; radio to pick one. Right: Multiselect invoices (with artist, show name, currency).
4. Centre: Compare bank amount vs sum of selected invoices; show difference; proxy adjustment and note; “Approve Match(es)” creates one handshake per selected invoice (split bank amount across them), updates invoice paid amounts and bank is_matched.
5. **Match table (Handshakes):** Below the three columns, a table of all handshakes (bank date, description, amount, invoice number, artist, event, amount applied, note, created_at). New matches appear here and disappear from the selection lists above.

**Logic:**
- Incoming only: `amount > 0`; outgoing transactions are excluded (no invoices for money out).
- One bank transaction can drive multiple handshakes (one per selected invoice); amount applied is min(remaining bank, invoice amount); proxy applied to first invoice only.
- After create: `st.rerun()` so selection lists and handshake table refresh.

**Reasoning:** Matching space stays focused on “what still needs matching”; once matched, items move conceptually “into” the handshake table below so the log is clear. Handshake table = same data as Handshakes page, in context.

---

### 4.4 Shows — `pages/4_Shows.py`

**Purpose:** View and search all shows (central hub). Search by artist, venue, promoter, contract number; filter by status; open a show to see details and related invoices/payments.

**Flow:**
1. Load shows (with optional search and filters from config: status, settlement status, agent).
2. Search box + filters (e.g. Show Status, Settlement Status, Agent).
3. Filtered show list; click a show → load show by id, related invoices, handshakes, outgoing, settlements; show detail view with settlement summary.

**Logic:**
- `load_shows(search=..., filters=...)` supports text search across several fields and exact filters. Config provides `SHOW_STATUSES`, `SETTLEMENT_STATUSES`, `AGENTS`.
- Settlement summary uses `calculate_show_settlement` (income vs outgo per show).

**Reasoning:** Shows are the anchor; this page is the place to see “everything about this gig” and to search/filter at scale.

---

### 4.5 Outgoing — `pages/5_Outgoing.py`

**Purpose:** Record outgoing payments from bank import (money out) or manually; view allocated vs all.

**Flow:**
1. **Record from bank (money out):** Load bank transactions with `outgoing_only=True` (amount &lt; 0). Exclude bank rows already linked to an outgoing payment. User selects one unallocated money-out transaction, optionally links to show, sets payment type and payee/notes → `create_outgoing_payment()` with `bank_id` set; amount/currency/date/description come from the bank row.
2. **Allocated money out:** Table of outgoing payments where `bank_id` is not null; merged with bank for date/description/amount (absolute). These are payments that were recorded from the bank import.
3. **Record payment (manual):** Form for payments not from bank: show, payment type, amount, currency, date, payee, description, notes. No `bank_id`. Submit → `create_outgoing_payment()`.
4. **Payment history:** All outgoing payments; filter by type and show; each row shows whether it is linked to a bank transaction.

**Logic:**
- Bank “money out” = `load_bank_transactions(outgoing_only=True)` (amount &lt; 0). Unallocated = bank rows whose `bank_id` is not in `outgoing_payments.bank_id`.
- Allocated = `outgoing_payments` where `bank_id` is not null. Merged with bank for display (bank amount shown as absolute).
- Payment type from config `OUTGOING_PAYMENT_TYPES`; optional `show_id` and `bank_id` for reconciliation.

**Reasoning:** Recording from bank import ties outgoing payments to actual bank debits; allocated section shows what’s reconciled; manual form covers payments not yet in the bank or from other sources.

---

### 4.6 Settlement — `pages/6_Settlement.py`

**Purpose:** Full settlement view per show and artist payment confirmation.

**Flow:**
1. Load shows, invoices, handshakes, outgoing, settlements.
2. Show selector (e.g. dropdown by artist @ venue).
3. For selected show: settlement calculation (income from handshakes, minus outgoing, fees, etc. via `calculate_show_settlement`); display amount due to artist, paid, balance.
4. Settlement record create/update (amount due, paid, status); “Confirm” sets status and confirmed_by/confirmed_at.
5. Optional: settlement email draft, export.

**Logic:**
- Settlement amounts come from utils (e.g. `calculate_show_settlement`), not recalculated ad hoc on the page.
- Status and confirmation stored in `settlements`; config provides `SETTLEMENT_STATUSES`.

**Reasoning:** “Full show settlement produced view and held in database” and “team confirm when they have paid the artist” are met by this page and the settlements table.

---

### 4.7 Handshakes — `pages/7_Handshakes.py`

**Purpose:** View and manage all bank–invoice matches (handshakes). Search, filter, delete wrong matches.

**Flow:**
1. Load all handshakes (with bank and invoice details from query).
2. If none: message + buttons to Match or Import; `st.stop()`.
3. Search (e.g. invoice number, description, note) and filter (e.g. With Proxy, No Proxy, With Notes).
4. Table of handshakes; optional “Delete” per row → `delete_handshake(id)` (reverses invoice paid amount and bank is_matched).
5. Summary stats (e.g. count, total applied).

**Logic:**
- `load_handshakes()` returns joined data (bank + invoice + show) for display.
- Delete restores invoice and bank state so the payment and invoice can be re-matched if needed.

**Reasoning:** Match page shows handshakes in context; this page is the full audit and correction surface.

---

### 4.8 Debug — `pages/8_Debug.py`

**Purpose:** Inspect DB for troubleshooting: tables, schemas, row counts, sample/full data.

**Flow:**
1. Get table list from DB; for each table: schema (PRAGMA table_info), count, sample rows (e.g. limit 100); expandable “View full table” for full data.
2. No writes; read-only.

**Logic:**
- Uses `get_db_connection()`, `get_table_info()`, and direct SQL for counts and data. No business logic.

**Reasoning:** Speeds up debugging and data verification without touching app code paths. Sensitive data warning in UI.

---

## 5. Shared components and config

- **utils/styling.py** — `apply_minimal_style()`: app-wide CSS (e.g. compact layout, colours). Applied on each page that calls it.
- **utils/app_theme.py** — Central theme/layout constants if used; may be used by styling.
- **utils/sidebar_nav.py** — Collapsed sidebar and deferred `st.switch_page()` (see §3).
- **utils/calculations.py** — e.g. `calculate_show_settlement`, `calculate_reconciliation_summary`; used by Dashboard, Shows, Settlement.
- **config/settings.py** — `DB_PATH`, `SHOW_STATUSES`, `SETTLEMENT_STATUSES`, `AGENTS`, `OUTGOING_PAYMENT_TYPES`, etc. Pages and importers use these for options and filters.
- **database/** — Schema (`schema.py`), connection (`connection.py`), queries (`queries.py`). All reads/writes go through these; no raw SQL in pages.

---

## 6. Keeping this documentation updated

**When you change the platform:**

1. **New or removed page**  
   - Add or remove a §4.x section.  
   - Update the Pages table in README if needed.

2. **Flow change on a page**  
   - Update the **Flow** bullets for that page in §4 so they match the current steps (e.g. new button, new filter, new table).

3. **Logic or business rule change**  
   - Update the **Logic** and, if needed, **Reasoning** for that page (e.g. new dedupe rule, new filter like `incoming_only`, new session-state behaviour).

4. **New shared component or config**  
   - Add a short note in §5 and, if it affects a page, mention it in that page’s section.

5. **Data model change**  
   - Update §2 (tables and roles) and any page that creates or uses the changed tables.

**Suggested workflow:** After each merge or release that touches behaviour, do a quick pass over this file and the README; update the sections that changed so the doc stays the single source of truth for flows, logic, and reasoning.

---

*Last structural update: Outgoing page — record from bank (money out), allocated money out section; Match page matching space only unmatched; handshake table below; sidebar session-state nav.*
