# LotTracker - Used Car Lot Inventory Management System

A self-hosted, web-based inventory management system built specifically for independent used car dealers. Track every vehicle from acquisition through reconditioning to sale, with full cost tracking, profit analysis, photo management, and multi-user support.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [First-Time Setup](#first-time-setup)
- [Running the Application](#running-the-application)
- [User Roles & Permissions](#user-roles--permissions)
- [Core Workflow](#core-workflow)
- [Vehicle Statuses](#vehicle-statuses)
- [Expense Categories](#expense-categories)
- [Reconditioning Stages](#reconditioning-stages)
- [Reports & KPIs](#reports--kpis)
- [Data Export](#data-export)
- [File Structure](#file-structure)
- [Configuration](#configuration)
- [Security Notes](#security-notes)
- [Troubleshooting](#troubleshooting)

---

## Features

### Vehicle Inventory
- Full vehicle tracking: VIN, year, make, model, trim, body type
- Exterior/interior color, mileage, transmission, engine, fuel type, drivetrain
- Lot location tracking (row, bay, section)
- Features/options list per vehicle
- Auto-generated stock numbers (S0001, S0002, ...)
- VIN uniqueness and format validation (17-char alphanumeric, no I/O/Q)
- Duplicate stock number prevention
- Clone vehicle — copy specs to a new stock number with one click
- Bulk status change — select multiple vehicles and update status at once
- Paginated inventory list (50 per page) with sort and search
- Days in recon tracking (separate from days on lot)

### Cost & Financial Tracking
- Purchase price (auto-logged as an expense at entry)
- Itemized expense tracking by category and subcategory
- Running total cost (purchase + all recon expenses)
- Asking price with potential profit preview
- Sale price recording with live profit calculation
- Gross profit per vehicle (sale price − total cost)

### Photo Management
- Upload multiple photos per vehicle (up to 30)
- Supported formats: JPG, JPEG, PNG, GIF, WebP
- Set a primary photo (shown as the vehicle thumbnail)
- Add captions to individual photos
- Lightbox viewer for full-size photo browsing
- Reorder and delete photos
- Photos stored in `static/uploads/vehicles/<id>/`

### Reconditioning Workflow
- 5-stage pipeline: Inspection → Mechanical → Body & Paint → Interior → Final QC
- Individual task cards per stage with title, description, priority
- Task statuses: Pending / In Progress / Done / Skipped
- Estimated vs. actual cost per task
- Vendor/shop assignment per task
- Staff assignment per task
- Due dates and completion dates
- One-click status updates from the vehicle detail page

### Activity Log
- Full audit trail per vehicle: every add, edit, expense, sale, and photo action is recorded
- Timestamp and user attributed to every log entry
- Log visible on the vehicle detail page

### Dashboard KPIs
- Active inventory count and total capital invested
- Average days on lot (target: < 30 days)
- Total gross profit across all sold vehicles
- Average gross profit per vehicle sold
- Aged inventory alerts: 30+, 60+, 90+ days
- Vehicles needing attention (In Recon > 7 days)
- Last 5 vehicles added
- 6-month sales chart (units sold + revenue)
- Inventory status donut chart

### Reports
| Report | Description |
|--------|-------------|
| Inventory Report | All vehicles with purchase, recon, and total costs; filterable by status |
| Profit & Loss | Sold vehicles with revenue, cost, and gross profit; filterable by year/month |
| Aging Report | Active vehicles grouped into 0–14, 15–30, 31–60, 61–90, 90+ day buckets |
| Expense Report | All expenses by category for a given year; category filter available |
| Performance Report | Average profit and days-on-lot by make; average profit by acquisition source |

### User Management
- Multi-user login with session-based authentication
- Three roles: Staff, Manager, Admin
- Admin-only user creation/editing
- User activate/deactivate toggle
- Self-service password change for all users (CSRF-protected form)
- Last login tracking
- Single remaining admin protection (can't demote or deactivate the last admin)

### Data Export
- Inventory CSV export (all vehicles with full cost breakdown)
- Sales CSV export (all sold vehicles with profit data)

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11+ / Flask 3.0 |
| Database | SQLite (via SQLAlchemy) |
| Auth | Flask-Login |
| Forms | Flask-WTF / WTForms |
| Frontend | Bootstrap 5.3 (dark theme) |
| Charts | Chart.js 4.4 |
| Icons | Bootstrap Icons 1.11 |

No external database server required. Everything runs on SQLite stored in a single file (`carlot.db`).

---

## Installation

### Prerequisites
- Python 3.9 or newer
- pip

### Step 1 – Clone or copy the project

```bash
# If cloning from git:
git clone <your-repo-url> shop-tracket
cd shop-tracket

# Or navigate to the project folder:
cd /path/to/Shop-tracket
```

### Step 2 – Create a virtual environment (recommended)

```bash
python3 -m venv venv

# Activate:
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### Step 3 – Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4 – Initialize the database

```bash
python3 app.py
```

On first run, this will:
1. Create the `carlot.db` SQLite database file
2. Create all required tables
3. Create a default admin account
4. Start the web server

You can then press `Ctrl+C` to stop it after the DB is initialized, or leave it running.

---

## First-Time Setup

1. Open your browser and go to: `http://localhost:5000`
2. Log in with the default credentials:
   - **Username:** `admin`
   - **Password:** `admin123`
3. **Immediately change your password** via the top-right menu → Change Password
4. Create additional user accounts via the **Users** menu (admin only)
5. Start adding vehicles via **Add Vehicle** or the `+` button in the navbar

---

## Running the Application

### Basic start

```bash
python3 app.py
```

The server starts on `http://0.0.0.0:5000`, accessible from any device on your local network.

### Run in the background (Linux)

```bash
nohup python3 app.py > lottracker.log 2>&1 &
echo "PID: $!"
```

To stop it:
```bash
kill <PID>
```

### Run as a systemd service (Linux, persistent across reboots)

Create `/etc/systemd/system/lottracker.service`:

```ini
[Unit]
Description=LotTracker Car Lot Management
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/Shop-tracket
ExecStart=/path/to/Shop-tracket/venv/bin/python3 app.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable lottracker
sudo systemctl start lottracker
sudo systemctl status lottracker
```

### Access from other computers on your network

Find your machine's local IP:
```bash
ip addr show | grep 'inet ' | grep -v 127.0.0.1
# Example: 192.168.1.50
```

Then on any device on the same network, visit: `http://192.168.1.50:5000`

---

## User Roles & Permissions

| Action | Staff | Manager | Admin |
|--------|-------|---------|-------|
| View all vehicles & reports | Yes | Yes | Yes |
| Add vehicles | Yes | Yes | Yes |
| Edit vehicles | Yes | Yes | Yes |
| Clone vehicles | Yes | Yes | Yes |
| Add expenses | Yes | Yes | Yes |
| Edit/delete own expenses | Yes | Yes | Yes |
| Edit/delete any expense | No | Yes | Yes |
| Add/edit recon tasks | Yes | Yes | Yes |
| Upload/delete own photos | Yes | Yes | Yes |
| Mark vehicles as sold | Yes | Yes | Yes |
| Bulk status change | Yes | Yes | Yes |
| Delete vehicles | No | Yes | Yes |
| Reverse sales | No | Yes | Yes |
| Manage users | No | No | Yes |
| Change own password | Yes | Yes | Yes |

---

## Core Workflow

### Adding a New Vehicle

1. Click **Add Vehicle** in the navbar
2. Fill in required fields: Stock #, Year, Make, Model, Purchase Date, Purchase Price
3. Select the acquisition source (Auction, Private Seller, etc.)
4. Set the initial status (usually **In Recon**)
5. Save — the purchase price is automatically recorded as an expense

### Cloning a Vehicle

To add a vehicle that shares specs with an existing one (e.g., same year/make/model batch):
1. Open the vehicle detail page or locate it in the inventory list
2. Click the **Clone** option in the action menu (or the Clone button on the detail page)
3. A new draft vehicle is created with the same specs but a new stock number and blank financial fields
4. The edit form opens immediately so you can adjust details

### Bulk Status Update

1. On the inventory list, check the boxes next to the vehicles you want to update
2. The bulk action bar appears at the top of the table
3. Select the new status from the dropdown and click **Apply**

### Tracking Reconditioning

1. Open the vehicle detail page
2. Under **Reconditioning Workflow**, click **Add Task** or the `+` next to a specific stage
3. Choose the stage, enter the task title and description
4. Set priority (Low / Normal / High / Urgent)
5. Enter estimated cost and vendor if known
6. As work progresses, update task status via the dropdown directly on the vehicle page

### Recording Expenses

1. Open the vehicle detail page or click **Add Expense** from the inventory list
2. Select the expense category (e.g., Mechanical > Brakes)
3. Enter the amount, vendor name, and date
4. Invoice number is optional but useful for record-keeping

### Adding Vehicle Photos

1. Open the vehicle detail page
2. Scroll to the **Photos** section and expand the upload panel
3. Select one or more images (JPG, PNG, GIF, or WebP; max 30 per vehicle)
4. Click **Upload Photos**
5. To set a photo as the primary image, click **Set Primary** below it
6. To remove a photo, click **Delete**

### Marking a Vehicle Sold

1. Open the vehicle detail page
2. Click the green **Mark Sold** button
3. Enter the sale date, sale price, and sale type
4. The system calculates and displays gross profit immediately
5. The vehicle status changes to **Sold**

To reverse a sale (manager/admin only): scroll to the Sale Record section and click **Reverse Sale**.

---

## Vehicle Statuses

| Status | Meaning |
|--------|---------|
| **In Recon** | Vehicle is being inspected or worked on, not yet for sale |
| **Available** | Ready for sale, on the lot |
| **Pending Sale** | Deal in progress, being held for a buyer |
| **Sold** | Vehicle has been sold; profit recorded |
| **Wholesale** | Sold to another dealer rather than retail |
| **On Hold** | Temporarily removed from sale for any reason |
| **Junked** | Vehicle scrapped or sent to crusher |

---

## Expense Categories

Expenses are organized in two levels: category and subcategory.

| Category | Subcategories |
|----------|--------------|
| **Mechanical** | Oil & Fluids, Brakes, Tires, Battery, Engine, Transmission, Suspension, Exhaust, AC/Heat, Electrical, Belts & Hoses, Steering, Cooling System, Fuel System, Other Mechanical |
| **Body & Paint** | Paint, Dent Repair, Body Panels, Bumper Repair, Glass/Windshield, Rust Repair, Frame Work, Other Body Work |
| **Interior** | Detailing, Upholstery, Carpet, Headliner, Dashboard, Seats, Odor Treatment, Window Tinting, Other Interior |
| **Tires & Wheels** | Tires, Wheels/Rims, Alignment, Balancing, TPMS Sensors |
| **Transportation** | Towing, Transport Fee, Fuel, Driver Fee |
| **Documentation** | Title Fee, DMV/Registration, Inspection Fee, History Report, Notary |
| **Advertising** | AutoTrader, Cars.com, Facebook Marketplace, Craigslist, Photography, Online Listing, Print Ad, Other Advertising |
| **Miscellaneous** | Keys/Locksmith, Floor Mats, License Plates, Touch-up Kit, Other |

> The purchase price is automatically categorized as `Purchase > Purchase Price` when a vehicle is added. It cannot be manually deleted — edit it via the Vehicle Edit form.

---

## Reconditioning Stages

| Stage | Typical Work |
|-------|-------------|
| **Inspection** | Initial condition assessment, test drive, identify issues, safety check |
| **Mechanical** | Engine, brakes, fluids, tires, belts, battery, AC, exhaust repairs |
| **Body & Paint** | Dents, scratches, rust, paint touch-up, windshield chips |
| **Interior** | Deep cleaning, odor treatment, upholstery repair, carpet, headliner |
| **Final QC** | Final walkthrough, re-test drive, verify all work complete, approve for sale |

Best practice target: complete the full reconditioning cycle within 3–5 business days.

---

## Reports & KPIs

### Dashboard KPIs Explained

| KPI | Target | Description |
|-----|--------|-------------|
| Avg Days on Lot | < 30 days | Average age of all active (unsold) vehicles |
| Aged 30+ | < 50% of lot | Vehicles at risk of losing profit |
| Aged 60+ | < 20% of lot | Significant concern; consider price reduction |
| Aged 90+ | < 5% of lot | Critical; wholesale or heavily discount |
| Avg Gross Profit | Varies | Revenue minus total costs per vehicle sold |

### Color-Coded Age Indicators

Throughout the app, days-on-lot badges use color coding:

- **Green** (0–29 days): Healthy, fresh inventory
- **Blue** (30–59 days): Monitor closely
- **Yellow** (60–89 days): Take action — reduce price or wholesale
- **Red** (90+ days): Critical — vehicle is costing money daily

Inventory rows on the list page are also highlighted yellow (60+ days) or red (90+ days) for at-a-glance awareness.

### Profit & Loss Report

Shows all vehicles sold in a selected year/month with:
- Total revenue collected
- Total cost of goods (purchase + all expenses)
- Gross profit (revenue − cost)
- Average gross profit per vehicle

### Performance Report

Analyzes your sold inventory to answer:
- Which makes generate the most profit on average?
- Which acquisition sources (auction, private, etc.) yield the best returns?

---

## Data Export

Two CSV exports are available under **Reports → Export**:

### Inventory CSV
Fields: Stock #, VIN, Year, Make, Model, Trim, Color, Mileage, Purchase Date, Purchase Price, Recon Cost, Total Cost, Asking Price, Status, Days on Lot, Title Status, Source, Lot Location, Notes

### Sales CSV
Fields: Stock #, Year, Make, Model, Purchase Date, Purchase Price, Recon Cost, Total Cost, Sale Date, Sale Price, Sale Type, Gross Profit, Days on Lot

Both files are named with today's date (e.g., `inventory_2026-04-06.csv`).

---

## File Structure

```
Shop-tracket/
├── app.py                  # Application factory, filters, entrypoint
├── config.py               # Configuration (secret key, database path)
├── models.py               # SQLAlchemy database models
├── forms.py                # WTForms form definitions
├── requirements.txt        # Python package dependencies
├── carlot.db               # SQLite database (created on first run)
│
├── routes/
│   ├── __init__.py
│   ├── activity.py         # Shared activity logging helper
│   ├── auth.py             # Login / logout
│   ├── vehicles.py         # Inventory CRUD, dashboard, bulk actions, clone
│   ├── expenses.py         # Expense add/edit/delete
│   ├── recon.py            # Reconditioning task CRUD
│   ├── sales.py            # Mark sold / reverse sale
│   ├── reports.py          # All reports + CSV export
│   ├── users.py            # User management + profile
│   ├── photos.py           # Vehicle photo upload/delete/set-primary
│   └── api.py              # JSON API for AJAX status updates
│
├── templates/
│   ├── base.html           # Base layout with navbar
│   ├── auth/
│   │   └── login.html
│   ├── errors/
│   │   ├── 403.html        # Forbidden error page
│   │   ├── 404.html        # Not found error page
│   │   └── 500.html        # Server error page
│   ├── vehicles/
│   │   ├── dashboard.html  # Main dashboard with KPIs and charts
│   │   ├── list.html       # Inventory table with filters, bulk actions, pagination
│   │   ├── form.html       # Add/edit vehicle form
│   │   └── detail.html     # Full vehicle detail with photos and activity log
│   ├── expenses/
│   │   └── form.html
│   ├── recon/
│   │   └── form.html
│   ├── reports/
│   │   ├── index.html
│   │   ├── inventory.html
│   │   ├── profit_loss.html
│   │   ├── aging.html
│   │   ├── expenses.html
│   │   └── performance.html
│   ├── users/
│   │   ├── list.html
│   │   ├── form.html
│   │   └── profile.html
│   └── sales/              # (handled via modal in detail.html)
│
└── static/
    ├── css/
    │   └── custom.css
    ├── js/
    │   └── custom.js
    └── uploads/
        └── vehicles/       # Vehicle photos stored here by vehicle ID
```

---

## Configuration

Edit `config.py` to change settings, or use environment variables:

```bash
# Generate a secure secret key:
python3 -c "import secrets; print(secrets.token_hex(32))"

# Set via environment variable (recommended):
export SECRET_KEY="your-generated-key"
python3 app.py
```

If `SECRET_KEY` is not set, the app will start with a default key and print a warning to stderr. **Always set a custom key in any real deployment.**

### Changing the port

Edit the last line of `app.py`:
```python
app.run(host='0.0.0.0', port=5000, debug=False)
# Change port=5000 to any port you prefer, e.g. port=8080
```

---

## Security Notes

**This application is designed for trusted local network use.** It is not hardened for public internet exposure. For local use on a private network, it is secure for day-to-day use. If you need to access it over the internet:

1. Put it behind a reverse proxy (nginx or Caddy) with HTTPS
2. Set a strong `SECRET_KEY` (not the default)
3. Change the default admin password immediately
4. Consider firewall rules to restrict access

**Passwords** are stored as bcrypt hashes using Werkzeug's `generate_password_hash`. They are never stored in plain text.

**CSRF protection** is enabled on all forms via Flask-WTF.

**SQL injection** is prevented by using SQLAlchemy's parameterized queries throughout.

**File uploads** are restricted to image types (jpg, jpeg, png, gif, webp) with UUID-based filenames to prevent path traversal or execution of uploaded files.

**Role-based access control** is enforced server-side on every route. Managers can delete vehicles and reverse sales; only admins can manage users. The last active admin account cannot be demoted or deactivated.

---

## Troubleshooting

### "Address already in use" on startup
Another process is using port 5000. Either stop that process or change the port in `app.py`.

```bash
# Find what's using port 5000:
lsof -i :5000
# Kill it:
kill -9 <PID>
```

### Database errors after an update
If the database schema changes (new columns added), the easiest fix is:
```bash
# Backup first!
cp carlot.db carlot.db.backup

# Then re-initialize (this recreates tables; existing data preserved with SQLAlchemy's create_all):
python3 -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### Forgotten admin password
```bash
python3 -c "
from app import app, db
from models import User
with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    if admin:
        admin.set_password('newpassword123')
        db.session.commit()
        print('Password reset to: newpassword123')
    else:
        print('No admin user found')
"
```

### Application won't start
Check that all dependencies are installed:
```bash
pip install -r requirements.txt
```

Check Python version (need 3.9+):
```bash
python3 --version
```

---

## Database Backup

Since the entire database is a single file (`carlot.db`), backups are simple:

```bash
# Manual backup:
cp carlot.db "carlot_backup_$(date +%Y%m%d).db"

# Automated daily backup (add to crontab):
# crontab -e
0 2 * * * cp /path/to/Shop-tracket/carlot.db /path/to/backups/carlot_$(date +\%Y\%m\%d).db
```

---

## Changelog

### v1.1.0
- Vehicle photo gallery (upload, lightbox, set primary, captions)
- Activity log per vehicle (full audit trail with user and timestamp)
- Clone vehicle action
- Bulk status change for multiple vehicles
- Paginated inventory list (50 per page)
- Days in recon metric (separate from days on lot)
- VIN format validation (17-char, no I/O/Q)
- Custom error pages (403, 404, 500)
- Password change form with proper CSRF protection
- Authorization enforced on expense and recon task edit/delete

### v1.0.0 (Initial Release)
- Full vehicle inventory management
- Multi-category expense tracking
- 5-stage reconditioning workflow
- Dashboard with live KPIs and charts
- Profit & Loss, Aging, Inventory, Expense, and Performance reports
- CSV data export
- Multi-user support with 3 permission levels
- CSRF-protected forms
- Responsive dark-theme UI
