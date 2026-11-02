# SoftobroCashBook 🇧🇩

> **A Production-Ready, Bangladesh-Based Multi-Tenant Business Cashbook & Financial Management SaaS Platform.**

SoftobroCashBook is a modern financial platform inspired by CashBook. It empowers businesses in Bangladesh to manage multiple businesses, cashbooks, cash-in transactions, cash-out transactions, live balances, and print-ready financial reports with genuine multi-tenant PostgreSQL database isolation.

---

## 🌟 Key Features

- **Multi-Tenant Database Isolation:** Every verified Service Admin (business owner) receives a dedicated, isolated PostgreSQL database provisioned on-the-fly. Zero risk of cross-tenant data leaks.
- **Role-Based Access Control (RBAC):**
  - **Super Admin:** Central dashboard, manage service admins, approve bKash payments, manage subscription plans, inspect & safely drop tenant databases, and review immutable audit logs.
  - **Service Admin:** Business registration, bKash payment submission, multi-business management, categorized cashbooks, cash-in/cash-out tracking, and real-time net balances.
- **Manual bKash Payment & Approval Workflow:**
  - Integrated bKash number presentation and one-click copy.
  - TrxID validation and optional screenshot receipt upload.
  - One-click Super Admin verification that calculates start/end dates, extends active subscriptions or starts new terms, provisions the tenant database, and sends in-app notifications.
- **Financial Accounting Engine:**
  - Accurate decimal precision (`DecimalField(max_digits=14, decimal_places=2)`) — zero floating-point inaccuracies.
  - Formula: $\text{Current Balance} = \text{Opening Balance} + \sum \text{Cash-In} - \sum \text{Cash-Out}$.
  - Category suggestions: Sales, Customer Payments, Salary, Office Rent, Utilities, Purchases, Drawings.
- **A4 Print & Statement Generator:**
  - Print-ready A4 stylesheets (`print.css`) for cashbooks, business summaries, and custom date-range ledgers.
  - Automatic suppression of navigation bars, buttons, and sidebars on print/PDF export.
  - Pre-formatted signature boxes (*Prepared By*, *Verified Accountant*, *Proprietor*).
- **Subscription Expiry Monitoring:**
  - Automated management command (`check_expiries`) for cPanel cron jobs.
  - Configurable grace period (default 7 days) and warnings 3 days before expiry.
- **Django REST Framework (DRF) API:**
  - Token-authenticated REST endpoints for future Android and iOS companion apps.
- **Modern UI / UX:**
  - Built with Bootstrap 5, Bootstrap Icons, and Chart.js.
  - Responsive sidebar, metric stat cards, and BDT (`৳`) currency formatting.

---

## 🏗️ Architecture & Technology Stack

| Component | Technology |
|---|---|
| **Backend Framework** | Python 3.12+ / Django 6.1+ |
| **Mobile / REST API** | Django REST Framework (TokenAuthentication) |
| **Databases** | PostgreSQL (Central Database + Dynamic Isolated Tenant Databases) |
| **Security & Cryptography** | `cryptography.fernet.Fernet` for encrypting tenant DB credentials |
| **Frontend** | Django Templates, HTML5, CSS3, JavaScript (ES6+), Bootstrap 5 |
| **Data Visualization** | Chart.js 4.4+ (Cash-In vs Cash-Out monthly trends) |
| **Deployment Engine** | cPanel / CloudLinux Passenger WSGI (`passenger_wsgi.py`) |

### Multi-Tenant Database Design

```
+-------------------------------------------------------------+
|               Central Platform Database                     |
|           (softobrocashbook_central)                        |
|                                                             |
|  - accounts_user (Super Admins, Service Admins)             |
|  - subscriptions_subscriptionplan                           |
|  - subscriptions_subscription                               |
|  - payments_payment (bKash Submissions & Approvals)         |
|  - tenants_tenant (Metadata & Encrypted DB Credentials)     |
|  - tenants_auditlog (Security & Administrative Audit Trail) |
|  - notifications_notification (In-app user alerts)          |
+-------------------------------------------------------------+
                              |
       +----------------------+----------------------+
       |                                             |
+-----------------------------+       +-----------------------------+
| Tenant DB 1: scb_tenant_2   |       | Tenant DB 2: scb_tenant_3   |
| (Dhaka General Trading Co.) |       | (Chittagong Retail Store)   |
|                             |       |                             |
| - businesses_business       |       | - businesses_business       |
| - cashbooks_cashbook        |       | - cashbooks_cashbook        |
| - transactions_transaction  |       | - transactions_transaction  |
| - django_migrations         |       | - django_migrations         |
+-----------------------------+       +-----------------------------+
```

---

## 🚀 Quickstart & Local Development

### 1. Prerequisites
- Python 3.10+
- PostgreSQL server running locally or accessible via network

### 2. Clone and Setup Environment
```powershell
# Clone the repository
git clone https://github.com/your-username/softobrocashbook.git
cd softobrocashbook

# Activate virtual environment
.\venv\Scripts\Activate.ps1   # On Windows
# or source venv/bin/activate # On Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env` and verify your PostgreSQL credentials:
```env
SECRET_KEY=django-insecure-your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=*

# Central Database (PostgreSQL)
CENTRAL_DB_ENGINE=django.db.backends.postgresql
CENTRAL_DB_NAME=softobrocashbook_central
CENTRAL_DB_USER=postgres
CENTRAL_DB_PASSWORD=postgres
CENTRAL_DB_HOST=localhost
CENTRAL_DB_PORT=5432

# Tenant Database Provisioning Settings
TENANT_DB_HOST=localhost
TENANT_DB_PORT=5432
TENANT_DB_SUPER_USER=postgres
TENANT_DB_SUPER_PASSWORD=postgres
TENANT_DB_PREFIX=scb_tenant_

# Security & Encryption (Fernet 32-byte url-safe key)
ENCRYPTION_KEY=b5q3L9DVOgq27l6htokTAYMt3nC3R3pzZu1WonV18mk=

# bKash Settings
BKASH_COMPANY_NUMBER=01712345678
BKASH_ACCOUNT_TYPE=Merchant / Personal
```

### 4. Migrate Central Database
```bash
python manage.py migrate
```

### 5. Seed Demo Data
Run our automated seeding command to generate sample subscription plans, the Super Admin, and a pre-configured demo Service Admin with provisioned tenant DB, sample businesses, and 8 transactions:
```bash
python manage.py seed_demo_data
```

**Default Seed Credentials:**
| Role | Username | Password | Email | Notes |
|---|---|---|---|---|
| **Super Admin** | `superadmin` | `Password@123` | `admin@softobrocashbook.com` | Full administrative access |
| **Demo Service Admin** | `demo_owner` | `Password@123` | `owner@dhakatrading.com` | Has active Growth Plan & `scb_tenant_2` DB |

### 6. Run the Development Server
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` in your browser.

---

## 🧪 Running the Automated Test Suite

The project includes unit and integration tests covering user roles, subscription limits, bKash payment verification, tenant routing isolation, decimal calculations, and REST APIs:

```bash
python manage.py test
```
*Expected result:* `Ran 12 tests in ~11s — OK`.

---

## 🌐 Production cPanel Deployment Guide

This project is tailored for deployment on cPanel shared or VPS hosting using **CloudLinux Python Selector / Passenger WSGI**.

### Step 1: Upload Project to cPanel
1. Compress your project files (excluding `venv/`, `.git/`, and `.env`) or clone directly via **cPanel Git Version Control**.
2. Place the project in a directory outside the public web root (e.g. `/home/username/softobrocashbook`).

### Step 2: Configure Python App in cPanel
1. Log into your cPanel account.
2. In the **Software** section, click **Setup Python App**.
3. Click **Create Application**:
   - **Python version:** Select `3.11` or `3.12`.
   - **Application root:** `softobrocashbook`
   - **Application URL:** your domain or subdomain (e.g., `app.yourdomain.com`).
   - **Application startup file:** `passenger_wsgi.py`
   - **Application Entry point:** `application`
4. Click **Create**.

### Step 3: Install Dependencies
1. Connect via SSH or use cPanel **Terminal**.
2. Enter the virtual environment command shown at the top of the Python App page:
   ```bash
   source /home/username/virtualenv/softobrocashbook/3.12/bin/activate
   cd /home/username/softobrocashbook
   ```
3. Install the required packages:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

### Step 4: Configure PostgreSQL Databases
1. In cPanel, navigate to **PostgreSQL Databases**.
2. Create the central database (e.g. `username_scb_central`).
3. Create a database user with strong password and grant **ALL PRIVILEGES** to the database.
4. Note that for tenant provisioning on shared cPanel hosting, ensure your database user has privileges to run `CREATE DATABASE` or configure the tenant settings in `.env`.

### Step 5: Setup Production `.env`
Create `/home/username/softobrocashbook/.env`:
```env
SECRET_KEY=generate-a-strong-50-character-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,app.yourdomain.com

CENTRAL_DB_ENGINE=django.db.backends.postgresql
CENTRAL_DB_NAME=username_scb_central
CENTRAL_DB_USER=username_dbuser
CENTRAL_DB_PASSWORD=your_strong_password
CENTRAL_DB_HOST=localhost
CENTRAL_DB_PORT=5432

TENANT_DB_HOST=localhost
TENANT_DB_PORT=5432
TENANT_DB_SUPER_USER=username_dbuser
TENANT_DB_SUPER_PASSWORD=your_strong_password
TENANT_DB_PREFIX=username_scb_t_

ENCRYPTION_KEY=generated-fernet-key
BKASH_COMPANY_NUMBER=017XXXXXXXX
BKASH_ACCOUNT_TYPE=Merchant
```

### Step 6: Collect Static Files & Migrate
```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py seed_demo_data # (Optional: seeds default subscription plans)
```

### Step 7: Configure Passenger WSGI & Restart
1. Verify `passenger_wsgi.py` exists at the root of `/home/username/softobrocashbook`.
2. In cPanel **Setup Python App**, click **Restart** to load the application.

### Step 8: Setup Subscription Expiry Cron Job
In cPanel **Cron Jobs**, add a daily cron to check expiring subscriptions and send user notifications:
```bash
0 2 * * * cd /home/username/softobrocashbook && /home/username/virtualenv/softobrocashbook/3.12/bin/python manage.py check_expiries >> /home/username/softobrocashbook/cron.log 2>&1
```

---

## 📱 Future Mobile App REST API Endpoints

The API is mounted under `/api/v1/` and uses TokenAuthentication (`Authorization: Token <token>`):

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/login/` | Authenticate and obtain API token + tenant status |
| `GET` | `/api/v1/auth/profile/` | Fetch current user profile & business info |
| `GET` | `/api/v1/summary/` | Get total businesses, cashbooks, cash-in, cash-out, net balance |
| `GET, POST` | `/api/v1/businesses/` | List and create businesses (enforces plan limit) |
| `GET, POST` | `/api/v1/cashbooks/` | List and create cashbooks per business |
| `GET, POST` | `/api/v1/transactions/` | Filter and record Cash-In / Cash-Out transactions |
| `GET` | `/api/v1/subscription/` | Current plan status, remaining days, and quotas |
| `GET, POST` | `/api/v1/payments/` | View submitted payments and submit new TrxID |
| `GET` | `/api/v1/notifications/` | In-app user notifications and mark-as-read action |

---

## 🛡️ License & Credits

Built by **Google DeepMind / Antigravity Agentic Team** for **Softobro Main**.  
Designed with care for business owners and accountants in Bangladesh.

