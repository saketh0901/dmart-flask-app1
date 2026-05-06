# DMart – Flask + MySQL Full-Stack Project
# ==========================================

## 📁 Project Structure

```
dmart/
├── app.py               ← Main Flask application (all routes & logic)
├── schema.sql           ← MySQL database schema + seed data
├── requirements.txt     ← Python dependencies
├── .env.example         ← Environment variable template
└── templates/
    ├── base.html        ← Shared layout (navbar, flash, footer)
    ├── index.html       ← Home page
    ├── products.html    ← Products listing with search & filter
    ├── product_detail.html
    ├── login.html
    ├── register.html
    ├── cart.html
    ├── checkout.html
    ├── orders.html
    ├── order_detail.html
    └── admin/
        ├── dashboard.html      ← Stats overview
        ├── products.html       ← Product CRUD
        ├── product_form.html   ← Add / Edit product form
        ├── orders.html         ← All orders + status update
        ├── customers.html      ← Customer spend summary
        └── customer_detail.html← Full itemised price list per customer
```

---

## ⚙️ Setup Instructions

### 1. Install MySQL & create database
```bash
mysql -u root -p < schema.sql
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables
Copy `.env.example` to `.env` and fill in your MySQL credentials:
```
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DB=dmart_db
SECRET_KEY=change-me-in-production
```

### 4. Run the app
```bash
python app.py
```
Visit → http://localhost:5000

---

## 🔑 Making yourself Admin
After registering your account, run in MySQL:
```sql
USE dmart_db;
UPDATE users SET is_admin = 1 WHERE email = 'your@email.com';
```
Then log in and click **⚙ Admin** in the navbar.

---

## ✅ Features Implemented

| Feature | Route |
|---|---|
| User Registration | /register |
| User Login / Logout | /login  /logout |
| Product Listing + Search + Filter | /products |
| Product Detail Page | /product/<id> |
| Add to Cart (DB-backed) | /cart/add/<id> |
| View & Update Cart | /cart |
| Checkout & Place Order | /checkout |
| Order History | /orders |
| Order Detail (itemised) | /orders/<id> |
| Admin Dashboard (stats) | /admin |
| Admin – Manage Products (CRUD) | /admin/products |
| Admin – Manage Orders + Status | /admin/orders |
| Admin – Customer List + Spend | /admin/customers |
| **Admin – Full Price List per Customer** | /admin/customers/<uid> |

---

## 🛠️ Tech Stack
- **Backend**: Python 3 + Flask
- **Database**: MySQL (via Flask-MySQLdb)
- **Auth**: Werkzeug password hashing + Flask session
- **Frontend**: Jinja2 templates, CSS variables, Google Fonts
- **No JS frameworks** – pure HTML/CSS with minimal inline JS
