# Arcade Pinball V3 - Talent Agency Show Reconciliation

A Streamlit web application for managing talent agency bookings, invoices, bank transactions, and settlements.

## Features

- **Shows Management**: Central hub for all artist bookings and performances
- **Invoice Tracking**: Create and track invoices sent to promoters
- **Bank Reconciliation**: Match bank transactions to invoices (handshakes); payments grouped by import batch or date
- **Artist Settlements**: Calculate and track payments to artists
- **Outgoing Payments**: Record and manage expenses (hotels, flights, etc.)
- **Real-time Dashboard**: Overview of financial status and pending actions
- **Data Import**: Import contracts, invoices, and bank transactions from CSV
- **Debug Tools**: Full database inspection and query interface
- **Collapsed Sidebar**: Icon-only nav that expands on hover; navigation uses session state (no callback no-op)

## Database Schema

The application uses SQLite with 8 interconnected tables:

1. **shows** - Central table for each booking/performance
2. **contracts** - Booking agreements from System One
3. **invoices** - Bills sent to promoters
4. **invoice_items** - Line items on each invoice
5. **bank_transactions** - Payments received (HSBC import)
6. **handshakes** - Links between bank transactions and invoices
7. **outgoing_payments** - Money paid out (artist fees, expenses)
8. **settlements** - Artist payment tracking

## Pages

Pages use ASCII-only filenames for reliable navigation and deployment:

| Page       | File               | Description                          |
|-----------|--------------------|--------------------------------------|
| Dashboard | `1_Dashboard.py`   | Overview and quick stats             |
| Import    | `2_Import.py`      | Import contracts, invoices, bank data |
| Match     | `3_Match.py`       | Link bank payments to invoices       |
| Shows     | `4_Shows.py`       | View and search all shows            |
| Outgoing  | `5_Outgoing.py`    | Manage outgoing payments             |
| Settlement| `6_Settlement.py`  | Artist settlement reports            |
| Handshakes| `7_Handshakes.py`  | View reconciliation matches          |
| Debug     | `8_Debug.py`       | Database inspection and tools        |

## Documentation

**Flows, logic, and reasoning** for every page are in **[docs/DOCUMENTATION.md](docs/DOCUMENTATION.md)**. It covers:

- Platform overview and data model
- App entry and sidebar navigation
- Per-page: purpose, flow, logic, reasoning
- Shared components and config
- **How to keep docs updated** when you change the platform

**Database schema, relationships, and integrity** (tables, columns, FKs, duplicate detection, handshake logic) are in **[docs/DATABASE_OVERVIEW.md](docs/DATABASE_OVERVIEW.md)**.

**When you update the platform:** update the relevant sections in `docs/DOCUMENTATION.md` (and this README if needed) so the docs stay the single source of truth.

## Installation

### Prerequisites
- Python 3.8+
- Git

### Setup
```bash
# Clone the repository
git clone <repository-url>
cd arcade-pinball-v3

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```

## Deployment to Streamlit Community Cloud

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. **Deploy to Streamlit**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with GitHub
   - Click "New app"
   - Select your repository, branch (main), and main file path (app.py)
   - Click "Deploy"

## Configuration

### Environment Variables
Create a `.streamlit/secrets.toml` file for production:
```toml
# Add any secrets or configuration here
```

### Database
- The app uses SQLite (`pinball.db`)
- Database is automatically initialized on first run
- For production, consider using PostgreSQL via Streamlit Secrets

## Data Import Formats

### Contracts (System One)
- CSV format with columns: `contract_number`, `artist`, `event_name`, `venue`, etc.

### Invoices
- CSV format with columns: `invoice_number`, `contract_number`, `total_gross`, etc.

### Bank Transactions (HSBC)
- CSV format with columns: `date`, `description`, `amount`, etc.

## Project Structure

- **`app.py`** – Main entry; sets page config, injects sidebar, redirects to Dashboard
- **`pages/`** – Multi-page app pages (ASCII filenames: `1_Dashboard.py`, `2_Import.py`, etc.)
- **`utils/`** – Shared UI and logic:
  - **`sidebar_nav.py`** – Collapsed icon sidebar (hover to expand), session-state navigation
  - **`app_theme.py`** – App-wide theme and layout
  - **`styling.py`** – Shared CSS and styling
  - **`calculations.py`** – Settlement and financial helpers
- **`database/`** – Schema, connection, and queries
- **`importers/`** – CSV importers for contracts, invoices, bank data
- **`config/`** – Settings and configuration

## Usage Notes

- **Fresh Database**: Each deployment starts with a fresh database unless you configure persistent storage
- **Data Export**: Use the export buttons on each page to download CSV backups
- **Debug Page**: Available at `/8_Debug` for troubleshooting

## License

Proprietary - For internal use by Arcade Talent Agency