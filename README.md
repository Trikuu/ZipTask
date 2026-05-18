# ZipTask

ZipTask is a clean Flask + PostgreSQL local task marketplace. Users post INR-budgeted tasks, other users request to join, task creators assign one performer, and completion releases 95% to the performer wallet and 5% to the platform admin wallet.

## Tech Stack

- Backend: Python, Flask, SQLAlchemy, Flask-Migrate
- Frontend: HTML, CSS, Bootstrap 5, JavaScript
- Database: PostgreSQL
- Payments: Razorpay Checkout
- Auth: JWT stored in an HTTP-only cookie, Werkzeug password hashing

## Folder Structure

```text
ZipTask/
├── app/
│   ├── static/
│   │   ├── css/styles.css
│   │   └── js/app.js
│   ├── templates/
│   │   ├── admin/panel.html
│   │   ├── auth/login.html
│   │   ├── auth/signup.html
│   │   ├── tasks/browse.html
│   │   ├── tasks/post.html
│   │   ├── wallet/index.html
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── home.html
│   │   ├── privacy.html
│   │   └── terms.html
│   ├── __init__.py
│   ├── admin_routes.py
│   ├── auth_routes.py
│   ├── auth_utils.py
│   ├── extensions.py
│   ├── main_routes.py
│   ├── models.py
│   ├── services.py
│   ├── task_routes.py
│   └── wallet_routes.py
├── migrations/
│   ├── versions/0001_initial_schema.py
│   ├── alembic.ini
│   ├── env.py
│   ├── README
│   └── script.py.mako
├── .env.example
├── .gitignore
├── Procfile
├── README.md
├── config.py
├── requirements.txt
├── runtime.txt
└── run.py
```

## Phase Summary

### Phase 1: Flask, PostgreSQL, Auth, Admin, Migrations

Files created:

- `run.py`, `config.py`
- `app/__init__.py`, `app/extensions.py`, `app/models.py`
- `app/auth_utils.py`, `app/auth_routes.py`, `app/main_routes.py`
- `app/profile_routes.py`
- `migrations/*`, `migrations/versions/0001_initial_schema.py`
- `app/templates/auth/*`, `app/templates/base.html`

Working features:

- Flask app factory
- PostgreSQL `DATABASE_URL` support, including Render's `postgres://` URL normalization
- Signup with full name, email, phone, password
- Privacy Policy and Terms acceptance during signup
- Login/logout with JWT cookie
- Password hashing
- Admin bootstrap from environment variables
- Database migrations

### Phase 2: Tasks

Files created:

- `app/task_routes.py`
- `app/templates/tasks/post.html`
- `app/templates/tasks/browse.html`
- Dashboard task actions in `app/templates/dashboard.html`

Working features:

- Create task with title, description, budget, and location
- Browse open, requested, assigned, and completed tasks
- Request to join open tasks
- Task creator reviews applicants and assigns one performer
- Mark assigned tasks complete

### Phase 3: Wallet and Razorpay

Files created:

- `app/wallet_routes.py`
- `app/templates/wallet/index.html`
- `app/static/js/app.js`

Working features:

- INR wallet balance and locked balance
- Transaction history
- Razorpay order creation
- Razorpay signature verification
- Wallet credit after verified payment
- No negative available balance for task locking
- Task completion split: 95% performer, 5% admin

### Phase 4: Admin Dashboard

Files created:

- `app/admin_routes.py`
- `app/templates/admin/panel.html`

Working features:

- Admin-only panel
- View users
- View tasks
- View transactions
- View total platform earnings
- Activate/deactivate users
- Soft-delete users while preserving audit records
- Filter tasks and transactions by date, user, and task status

### Password Reset

Files created/updated:

- `app/templates/auth/forgot_password.html`
- `app/templates/auth/reset_password.html`
- `app/auth_routes.py`
- `app/services.py`

Working features:

- Forgot Password link on login page
- Email reset request through SMTP
- Secure signed reset token
- 30-minute token expiry
- Password reset using the same password rules as signup

## Local Setup

### 1. Create PostgreSQL database

Create a local PostgreSQL database named `ziptask`.

```powershell
createdb ziptask
```

If your PostgreSQL user, password, host, or port differs, update `DATABASE_URL` in `.env`.

### 2. Create and activate virtual environment

```powershell
cd C:\Users\chait\OneDrive\Desktop\projects\ZipTask
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Configure environment

```powershell
Copy-Item .env.example .env
```

Edit `.env`:

```env
SECRET_KEY=your-long-random-secret
JWT_SECRET_KEY=your-long-random-jwt-secret
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ziptask
DEFAULT_ADMIN_EMAIL=admin@ziptask.in
DEFAULT_ADMIN_PASSWORD=ChangeAdminPassword123!
DEFAULT_ADMIN_PHONE=9110766718
RAZORPAY_KEY_ID=rzp_test_your_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-app-password
MAIL_USE_TLS=true
```

### 4. Run migrations and bootstrap admin

```powershell
$env:FLASK_APP="run.py"
python -m flask db upgrade
python -m flask bootstrap-admin
```

The app uses Flask-Migrate for schema changes. Do not rely on startup `create_all()` in production. The app also verifies the admin account on startup only after the `users` table exists.

### Database and Auth Reliability

ZipTask now includes:

- Normalized `DATABASE_URL` handling for Render `postgres://` URLs.
- SQLAlchemy connection pooling with `pool_pre_ping` and recycle settings.
- `/health` endpoint that checks database connectivity with `SELECT 1`.
- Idempotent admin bootstrap that does not delete existing admin records.
- JWT auth stored in an HTTP-only cookie.
- Expired/invalid auth cookies are cleared automatically.
- Protected routes redirect to `/auth/login`.
- Duplicate users are blocked by database constraints and backend checks.
- Login attempt rate limiting is enabled in-process.
- Database errors are logged and rolled back safely.

### 5. Run the app

```powershell
python -m flask run
```

Open `http://127.0.0.1:5000`.

## Admin Credentials

Admin credentials are configured in `.env`:

```env
DEFAULT_ADMIN_EMAIL=admin@ziptask.in
DEFAULT_ADMIN_PASSWORD=ChangeAdminPassword123!
DEFAULT_ADMIN_PHONE=9110766718
```

Change these before first production deployment. `DEFAULT_ADMIN_PHONE` is used when `python -m flask bootstrap-admin` creates or updates the admin account. After deployment, login with the admin email and password at `/auth/login`. Admin users are redirected to `/admin`, and the admin panel is also available at:

```text
/admin/
```

## Razorpay Setup

### Create a Razorpay account

1. Go to [Razorpay](https://razorpay.com/).
2. Sign up with your business email and phone number.
3. Complete business profile and KYC details.
4. Use Test Mode while developing.

### Get API keys

1. Open the Razorpay Dashboard.
2. Switch to Test Mode for development.
3. Go to Account & Settings → API Keys.
4. Generate a key pair.
5. Copy `Key ID` to `RAZORPAY_KEY_ID`.
6. Copy `Key Secret` to `RAZORPAY_KEY_SECRET`.

### Connect a bank account

1. In Razorpay Dashboard, complete KYC.
2. Go to Account & Settings → Bank Account.
3. Add your current account or supported business bank account.
4. Verify the account as requested by Razorpay.
5. Switch to Live Mode only after Razorpay activates your account.

## Render Deployment

### 1. Push to GitHub

```powershell
cd C:\Users\chait\OneDrive\Desktop\projects\ZipTask
git init
git add .
git commit -m "Initial ZipTask app"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ZipTask.git
git push -u origin main
```

### 2. Create PostgreSQL on Render

1. Open Render Dashboard.
2. Create a new PostgreSQL database.
3. Copy the internal database URL.

### 3. Create Web Service

1. Create a new Web Service from your GitHub repository.
2. Runtime: Python.
3. Build command:

```bash
pip install -r requirements.txt && python -m flask db upgrade && python -m flask bootstrap-admin
```

4. Start command:

```bash
gunicorn run:app
```

### 4. Add Render environment variables

Set:

```env
FLASK_ENV=production
FLASK_APP=run.py
SECRET_KEY=your-production-secret
JWT_SECRET_KEY=your-production-jwt-secret
DATABASE_URL=your-render-postgresql-internal-url
COOKIE_SECURE=true
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DEFAULT_ADMIN_EMAIL=your-admin-email
DEFAULT_ADMIN_PASSWORD=your-strong-admin-password
DEFAULT_ADMIN_PHONE=9110766718
RAZORPAY_KEY_ID=your-live-or-test-key-id
RAZORPAY_KEY_SECRET=your-live-or-test-key-secret
MAIL_SERVER=your-smtp-host
MAIL_PORT=587
MAIL_USERNAME=your-smtp-username
MAIL_PASSWORD=your-smtp-password
MAIL_USE_TLS=true
```

Render sometimes provides PostgreSQL URLs starting with `postgres://`. ZipTask automatically converts this to SQLAlchemy's required `postgresql://` format, so login and database access work correctly after deployment.

### Production deploy commands

Build command:

```bash
pip install -r requirements.txt && python -m flask db upgrade && python -m flask bootstrap-admin
```

Start command:

```bash
gunicorn run:app
```

Health check path:

```text
/health
```

## Payment Flow

1. User adds money from Wallet using Razorpay.
2. Backend creates a Razorpay order.
3. Razorpay Checkout collects payment.
4. Backend verifies `razorpay_order_id`, `razorpay_payment_id`, and `razorpay_signature`.
5. Wallet is credited only after signature verification.
6. Other users request to join a task.
7. The task creator assigns one applicant.
8. When assigned, the creator's task budget is locked.
9. When the creator marks it complete:
   - 95% is credited to performer wallet.
   - 5% is credited to admin wallet.
   - The locked amount is deducted from creator wallet.

## Important Routes

- `/` Home
- `/auth/signup` Signup
- `/auth/login` Login
- `/dashboard` Dashboard
- `/tasks/post` Post task
- `/tasks/` Browse tasks
- `/wallet/` Wallet
- `/admin/` Admin panel
- `/privacy-policy` Privacy Policy
- `/terms` Terms & Conditions
