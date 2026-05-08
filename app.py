"""
DMart – Flask + MySQL Full‑Stack Application
=============================================
Run:
    pip install -r requirements.txt
    # Import schema first:  mysql -u root -p < schema.sql
    python app.py
"""

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify
)
import pymysql
pymysql.install_as_MySQLdb()
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
from dotenv import load_dotenv  
load_dotenv()  

app = Flask(__name__)

# ─── Config ─────────────────────────────────────────────────
app.secret_key = os.environ.get("SECRET_KEY", "dmart-super-secret-2024")

app.config["MYSQL_HOST"]     = os.environ.get("MYSQL_HOST", "localhost")
app.config["MYSQL_USER"]     = os.environ.get("MYSQL_USER", "root")
app.config["MYSQL_PASSWORD"] = os.environ.get("MYSQL_PASSWORD", "dmart123")
app.config["MYSQL_DB"]       = os.environ.get("MYSQL_DB", "dmart_db")
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)

# ─── Helpers ─────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Admin access required.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated

def get_cart_count():
    if "user_id" not in session:
        return 0
    cur = mysql.connection.cursor()
    cur.execute("SELECT SUM(quantity) AS cnt FROM cart WHERE user_id=%s",
                (session["user_id"],))
    row = cur.fetchone()
    cur.close()
    return int(row["cnt"] or 0)

# Inject cart count into every template
@app.context_processor
def inject_cart():
    return dict(cart_count=get_cart_count())


# ══════════════════════════════════════════════════════════════
#  PUBLIC ROUTES
# ══════════════════════════════════════════════════════════════

@app.route("/")
def index():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM categories")
    categories = cur.fetchall()
    cur.execute("""
        SELECT p.*, c.name AS category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        ORDER BY p.id DESC LIMIT 12
    """)
    products = cur.fetchall()
    cur.close()
    return render_template("index.html", categories=categories, products=products)


@app.route("/products")
def products():
    search  = request.args.get("q", "").strip()
    cat_id  = request.args.get("category", "")
    cur = mysql.connection.cursor()

    query  = """
        SELECT p.*, c.name AS category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND (p.name LIKE %s OR p.description LIKE %s)"
        params += [f"%{search}%", f"%{search}%"]
    if cat_id:
        query += " AND p.category_id = %s"
        params.append(cat_id)

    query += " ORDER BY p.name"
    cur.execute(query, params)
    items = cur.fetchall()

    cur.execute("SELECT * FROM categories")
    categories = cur.fetchall()
    cur.close()
    return render_template("products.html", products=items,
                           categories=categories, search=search, cat_id=cat_id)


@app.route("/product/<int:pid>")
def product_detail(pid):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT p.*, c.name AS category_name
        FROM products p LEFT JOIN categories c ON p.category_id=c.id
        WHERE p.id=%s
    """, (pid,))
    product = cur.fetchone()
    cur.close()
    if not product:
        flash("Product not found.", "warning")
        return redirect(url_for("products"))
    return render_template("product_detail.html", product=product)


# ══════════════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════════════cd C:\Users\kodav\OneDrive\Desktop\dmart_project\dmart

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email    = request.form["email"].strip()
        password = request.form["password"]
        confirm  = request.form["confirm_password"]

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))

        hashed = generate_password_hash(password)
        cur = mysql.connection.cursor()
        try:
            cur.execute(
                "INSERT INTO users (username, email, password) VALUES (%s,%s,%s)",
                (username, email, hashed)
            )
            mysql.connection.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))
        except Exception:
            flash("Username or email already exists.", "danger")
        finally:
            cur.close()

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form["email"].strip()
        password = request.form["password"]

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"]  = user["id"]
            session["username"] = user["username"]
            session["is_admin"] = bool(user["is_admin"])
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(url_for("index"))
        flash("Invalid email or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# ══════════════════════════════════════════════════════════════
#  CART
# ══════════════════════════════════════════════════════════════

@app.route("/cart")
@login_required
def cart():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT c.id, c.quantity, p.name, p.price, p.image_url,
               (c.quantity * p.price) AS subtotal
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = %s
    """, (session["user_id"],))
    items = cur.fetchall()
    cur.close()
    total = sum(i["subtotal"] for i in items)
    return render_template("cart.html", items=items, total=total)


@app.route("/cart/add/<int:pid>", methods=["POST"])
@login_required
def add_to_cart(pid):
    qty = int(request.form.get("quantity", 1))
    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO cart (user_id, product_id, quantity)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE quantity = quantity + %s
    """, (session["user_id"], pid, qty, qty))
    mysql.connection.commit()
    cur.close()
    flash("Item added to cart!", "success")
    return redirect(request.referrer or url_for("products"))


@app.route("/cart/update/<int:cid>", methods=["POST"])
@login_required
def update_cart(cid):
    qty = int(request.form.get("quantity", 1))
    cur = mysql.connection.cursor()
    if qty <= 0:
        cur.execute("DELETE FROM cart WHERE id=%s AND user_id=%s",
                    (cid, session["user_id"]))
    else:
        cur.execute("UPDATE cart SET quantity=%s WHERE id=%s AND user_id=%s",
                    (qty, cid, session["user_id"]))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for("cart"))


@app.route("/cart/remove/<int:cid>")
@login_required
def remove_from_cart(cid):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM cart WHERE id=%s AND user_id=%s",
                (cid, session["user_id"]))
    mysql.connection.commit()
    cur.close()
    flash("Item removed.", "info")
    return redirect(url_for("cart"))


# ══════════════════════════════════════════════════════════════
#  CHECKOUT & ORDERS
# ══════════════════════════════════════════════════════════════

@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT c.quantity, p.price, p.name, p.id AS product_id, p.stock
        FROM cart c JOIN products p ON c.product_id=p.id
        WHERE c.user_id=%s
    """, (session["user_id"],))
    items = cur.fetchall()

    if not items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("cart"))

    total = sum(i["quantity"] * i["price"] for i in items)

    if request.method == "POST":
        # Check stock
        for item in items:
            if item["quantity"] > item["stock"]:
                flash(f"Insufficient stock for {item['name']}.", "danger")
                return redirect(url_for("cart"))

        # Create order
        cur.execute(
            "INSERT INTO orders (user_id, total_price) VALUES (%s,%s)",
            (session["user_id"], total)
        )
        order_id = cur.lastrowid

        for item in items:
            cur.execute(
                "INSERT INTO order_items (order_id,product_id,quantity,unit_price) VALUES(%s,%s,%s,%s)",
                (order_id, item["product_id"], item["quantity"], item["price"])
            )
            cur.execute(
                "UPDATE products SET stock=stock-%s WHERE id=%s",
                (item["quantity"], item["product_id"])
            )

        cur.execute("DELETE FROM cart WHERE user_id=%s", (session["user_id"],))
        mysql.connection.commit()
        cur.close()
        flash("Order placed successfully! 🎉", "success")
        return redirect(url_for("order_history"))

    cur.close()
    return render_template("checkout.html", items=items, total=total)


@app.route("/orders")
@login_required
def order_history():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT o.id, o.total_price, o.status, o.created_at
        FROM orders o
        WHERE o.user_id=%s ORDER BY o.created_at DESC
    """, (session["user_id"],))
    orders = cur.fetchall()
    cur.close()
    return render_template("orders.html", orders=orders)


@app.route("/orders/<int:oid>")
@login_required
def order_detail(oid):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM orders WHERE id=%s AND user_id=%s",
                (oid, session["user_id"]))
    order = cur.fetchone()
    if not order:
        flash("Order not found.", "warning")
        return redirect(url_for("order_history"))

    cur.execute("""
        SELECT oi.quantity, oi.unit_price,
               (oi.quantity * oi.unit_price) AS line_total,
               p.name, p.image_url
        FROM order_items oi JOIN products p ON oi.product_id=p.id
        WHERE oi.order_id=%s
    """, (oid,))
    items = cur.fetchall()
    cur.close()
    return render_template("order_detail.html", order=order, items=items)


# ══════════════════════════════════════════════════════════════
#  ADMIN PANEL
# ══════════════════════════════════════════════════════════════

@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) AS cnt FROM users")
    user_count = cur.fetchone()["cnt"]
    cur.execute("SELECT COUNT(*) AS cnt FROM orders")
    order_count = cur.fetchone()["cnt"]
    cur.execute("SELECT SUM(total_price) AS rev FROM orders WHERE status!='cancelled'")
    revenue = cur.fetchone()["rev"] or 0
    cur.execute("SELECT COUNT(*) AS cnt FROM products")
    product_count = cur.fetchone()["cnt"]
    cur.execute("""
        SELECT o.id, o.total_price, o.status, o.created_at, u.username
        FROM orders o JOIN users u ON o.user_id=u.id
        ORDER BY o.created_at DESC LIMIT 10
    """)
    recent_orders = cur.fetchall()
    cur.close()
    return render_template("admin/dashboard.html",
                           user_count=user_count, order_count=order_count,
                           revenue=revenue, product_count=product_count,
                           recent_orders=recent_orders)


@app.route("/admin/products")
@login_required
@admin_required
def admin_products():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT p.*, c.name AS category_name
        FROM products p LEFT JOIN categories c ON p.category_id=c.id
        ORDER BY p.id DESC
    """)
    products = cur.fetchall()
    cur.close()
    return render_template("admin/products.html", products=products)


@app.route("/admin/products/add", methods=["GET", "POST"])
@login_required
@admin_required
def admin_add_product():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM categories")
    categories = cur.fetchall()

    if request.method == "POST":
        name     = request.form["name"].strip()
        desc     = request.form["description"].strip()
        price    = float(request.form["price"])
        stock    = int(request.form["stock"])
        img      = request.form["image_url"].strip()
        cat_id   = request.form["category_id"]
        cur.execute(
            "INSERT INTO products (name,description,price,stock,image_url,category_id) VALUES(%s,%s,%s,%s,%s,%s)",
            (name, desc, price, stock, img, cat_id)
        )
        mysql.connection.commit()
        cur.close()
        flash("Product added!", "success")
        return redirect(url_for("admin_products"))

    cur.close()
    return render_template("admin/product_form.html", categories=categories, product=None)


@app.route("/admin/products/edit/<int:pid>", methods=["GET", "POST"])
@login_required
@admin_required
def admin_edit_product(pid):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products WHERE id=%s", (pid,))
    product = cur.fetchone()
    cur.execute("SELECT * FROM categories")
    categories = cur.fetchall()

    if request.method == "POST":
        name   = request.form["name"].strip()
        desc   = request.form["description"].strip()
        price  = float(request.form["price"])
        stock  = int(request.form["stock"])
        img    = request.form["image_url"].strip()
        cat_id = request.form["category_id"]
        cur.execute("""
            UPDATE products SET name=%s,description=%s,price=%s,
            stock=%s,image_url=%s,category_id=%s WHERE id=%s
        """, (name, desc, price, stock, img, cat_id, pid))
        mysql.connection.commit()
        cur.close()
        flash("Product updated!", "success")
        return redirect(url_for("admin_products"))

    cur.close()
    return render_template("admin/product_form.html", product=product, categories=categories)


@app.route("/admin/products/delete/<int:pid>")
@login_required
@admin_required
def admin_delete_product(pid):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM products WHERE id=%s", (pid,))
    mysql.connection.commit()
    cur.close()
    flash("Product deleted.", "info")
    return redirect(url_for("admin_products"))


@app.route("/admin/orders")
@login_required
@admin_required
def admin_orders():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT o.id, o.total_price, o.status, o.created_at, u.username, u.email
        FROM orders o JOIN users u ON o.user_id=u.id
        ORDER BY o.created_at DESC
    """)
    orders = cur.fetchall()
    cur.close()
    return render_template("admin/orders.html", orders=orders)


@app.route("/admin/orders/update/<int:oid>", methods=["POST"])
@login_required
@admin_required
def admin_update_order(oid):
    status = request.form["status"]
    cur = mysql.connection.cursor()
    cur.execute("UPDATE orders SET status=%s WHERE id=%s", (status, oid))
    mysql.connection.commit()
    cur.close()
    flash("Order status updated.", "success")
    return redirect(url_for("admin_orders"))


@app.route("/admin/customers")
@login_required
@admin_required
def admin_customers():
    """Full price list per customer — all orders with itemised breakdown."""
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT u.id, u.username, u.email,
               COUNT(DISTINCT o.id)          AS total_orders,
               COALESCE(SUM(o.total_price),0) AS total_spent
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id AND o.status != 'cancelled'
        WHERE u.is_admin = 0
        GROUP BY u.id
        ORDER BY total_spent DESC
    """)
    customers = cur.fetchall()
    cur.close()
    return render_template("admin/customers.html", customers=customers)


@app.route("/admin/customers/<int:uid>")
@login_required
@admin_required
def admin_customer_detail(uid):
    """Itemised order history for a single customer."""
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, username, email FROM users WHERE id=%s", (uid,))
    customer = cur.fetchone()

    cur.execute("""
        SELECT o.id AS order_id, o.total_price, o.status, o.created_at
        FROM orders o WHERE o.user_id=%s ORDER BY o.created_at DESC
    """, (uid,))
    orders = cur.fetchall()

    # Attach line items to each order
    for order in orders:
        cur.execute("""
            SELECT p.name, oi.quantity, oi.unit_price,
                   (oi.quantity*oi.unit_price) AS line_total
            FROM order_items oi JOIN products p ON oi.product_id=p.id
            WHERE oi.order_id=%s
        """, (order["order_id"],))
        order["items"] = cur.fetchall()

    cur.close()
    return render_template("admin/customer_detail.html",
                           customer=customer, orders=orders)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
