import os
import re
import smtplib
import threading
import uuid
import calendar
from datetime import date, datetime, timedelta
from email.mime.text import MIMEText
from functools import wraps

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from models import MenuItem, Order, OrderItem, PickupSlot, User, db


app = Flask(__name__)
app.secret_key = "mothers_kitchen_secret_key"

# Database Configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'mothers_kitchen.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "images", "menu")

# Link SQLAlchemy instance to Flask app
db.init_app(app)

# Bank Details
PAYID = "hello@motherskitchen.com.au"
BANK_NAME = "XXX Bank"
BANK_ACCOUNT_NAME = "Mother's Kitchen"
BANK_BSB = "XXX-XXX"
BANK_ACCOUNT_NUMBER = "XXXX XXXX"

# Business Details
BUSINESS_PHONE = "0444 503 867"
BUSINESS_EMAIL = "weserve@motherskitchen.com.au"
BUSINESS_HOURS = "Tuesday - Sunday, 11:00 AM - 7:00 PM"
BUSINESS_ADDRESS = "6 Universal Road, Tarneit, VIC, 3029"

MAX_BOOKINGS_PER_SLOT = 5

# Validation helpers
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def is_blank(value):
    return value is None or value.strip() == ""

def login_required(view_function):
    @wraps(view_function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return view_function(*args, **kwargs)

    return wrapper

# admin required function
def admin_required(view_function):
    @wraps(view_function)
    def wrapper(*args, **kwargs):
        if session.get("account_type") != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("login"))
        return view_function(*args, **kwargs)

    return wrapper

# Home Route
@app.route("/")
def home():
    return render_template(
        "home.html",
        tagline="Made with Love, Served Warm.",
        business_phone="0400 123 456",
        business_email="contact@motherskitchen.com.au",
        business_hours="Mon - Sat: 11:00 AM - 8:00 PM",
        business_address="123 Home Street, Tarneit VIC 3029",
        current_year=datetime.now().year
    )

#images
def save_menu_image(file_storage):
    """Saves an uploaded photo and returns its new URL, or None if no file was given."""
    if not file_storage or file_storage.filename == "":
        return None

    extension = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Unsupported file type. Please upload a PNG, JPG, JPEG, GIF, or WEBP image.")

    # Add a random prefix so two people uploading "naan.jpg" don't overwrite each other.
    unique_name = f"{uuid.uuid4().hex}_{secure_filename(file_storage.filename)}"
    file_storage.save(os.path.join(UPLOAD_FOLDER, unique_name))
    return f"/static/images/menu/{unique_name}"


def delete_menu_image(image_url):
    """Deletes a previously uploaded photo file, if this URL points to one."""
    if not image_url or not image_url.startswith("/static/images/menu/"):
        return  # It's an external URL (or empty) -- nothing to delete.
    file_path = os.path.join(UPLOAD_FOLDER, image_url.rsplit("/", 1)[-1])
    if os.path.isfile(file_path):
        os.remove(file_path)


# Login Home Route
@app.route("/home2")
@login_required
def home2():
    return render_template("home2.html")

# Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        account_type = request.form.get("account_type", "customer")

        if is_blank(email) or is_blank(password):
            flash("Email and password are required.", "error")
            return render_template("login.html")

        if not EMAIL_RE.match(email.strip()):
            flash("Please enter a valid email address.", "error")
            return render_template("login.html")

        if account_type not in ("customer", "admin"):
            flash("Invalid account type selected.", "error")
            return render_template("login.html")

        user = User.query.filter_by(email=email.strip().lower()).first()

        if not user or not user.check_password(password):
            flash("Incorrect email or password.", "error")
            return render_template("login.html")

        if user.account_type != account_type:
            flash(
                f"This account is registered as '{user.account_type}', "
                f"not '{account_type}'. Please pick the correct account type.",
                "error",
            )
            return render_template("login.html")

        session["user_id"] = user.id
        session["user_name"] = user.name
        session["account_type"] = user.account_type

        if user.account_type == "admin":
            return redirect(url_for("admin_home"))
        return redirect(url_for("home2"))

    return render_template("login.html")

# Signup Route
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "")
        email = request.form.get("email", "")
        mobile = request.form.get("mobile_number", "")
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if is_blank(name) or is_blank(email) or is_blank(mobile) or is_blank(password):
            flash("Name, email, mobile number, and password are all required.", "error")
            return render_template("signup.html")

        if not EMAIL_RE.match(email.strip()):
            flash("Please enter a valid email address.", "error")
            return render_template("signup.html")

        if not re.match(r"^\+?[0-9\-\s]{7,15}$", mobile.strip()):
            flash("Please enter a valid mobile number.", "error")
            return render_template("signup.html")

        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "error")
            return render_template("signup.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("signup.html")

        if User.query.filter_by(email=email.strip().lower()).first():
            flash("An account with that email already exists. Please log in.", "error")
            return redirect(url_for("login"))

        user = User(
            name=name.strip(),
            email=email.strip().lower(),
            mobile_number=mobile.strip(),
            account_type="customer",
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        session["user_id"] = user.id
        session["user_name"] = user.name
        session["account_type"] = user.account_type

        flash(f"Welcome to Mother's Kitchen, {user.name}!", "success")
        return redirect(url_for("home2"))

    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


@app.route("/menu")
@login_required
def menu():
    """Shows every available dish. Supports a search box and dietary filters."""
    query_text = request.args.get("q", "").strip()
    selected_diets = request.args.getlist("diet")

    items_query = MenuItem.query.filter_by(is_available=True)

    if query_text:
        like_pattern = f"%{query_text}%"
        items_query = items_query.filter(
            db.or_(MenuItem.name.ilike(like_pattern), MenuItem.description.ilike(like_pattern))
        )

    diet_column_map = {
        "vegan": MenuItem.is_vegan,
        "gluten_free": MenuItem.is_gluten_free,
        "dairy_free": MenuItem.is_dairy_free,
        "nut_free": MenuItem.is_nut_free,
    }
    for diet in selected_diets:
        column = diet_column_map.get(diet)
        if column is not None:
            items_query = items_query.filter(column.is_(True))

    items = items_query.order_by(MenuItem.category, MenuItem.name).all()
    return render_template("menu.html", items=items, query_text=query_text, selected_diets=selected_diets)


@app.route("/menu/<int:item_id>")
@login_required
def item_detail(item_id):
    item = MenuItem.query.get_or_404(item_id)
    return render_template("item_detail.html", item=item)

# cart
def get_cart():
    return session.setdefault("cart", {})

@app.route("/cart")
@login_required
def cart():
    cart = get_cart()
    details = []
    total = 0.0
    for item_id_str, qty in cart.items():
        item = MenuItem.query.get(int(item_id_str))
        if item is None:
            continue
        subtotal = item.price * qty
        total += subtotal
        details.append({"item": item, "quantity": qty, "subtotal": subtotal})
    return render_template("cart.html", details=details, total=total)

@app.route("/cart/add/<int:item_id>", methods=["POST"])
@login_required
def add_to_cart(item_id):
    item = MenuItem.query.get_or_404(item_id)
    if not item.is_available:
        flash(f"Sorry, {item.name} is sold out.", "error")
        return redirect(url_for("menu"))

    cart = get_cart()
    key = str(item_id)
    cart[key] = cart.get(key, 0) + 1
    session.modified = True
    flash(f"Added {item.name} to your cart.", "success")
    return redirect(request.referrer or url_for("menu"))

@app.route("/cart/remove/<int:item_id>", methods=["POST"])
@login_required
def remove_from_cart(item_id):
    cart = get_cart()
    cart.pop(str(item_id), None)
    session.modified = True
    flash("Item removed from cart.", "success")
    return redirect(url_for("cart"))


@app.route("/cart/update/<int:item_id>", methods=["POST"])
@login_required
def update_cart(item_id):
    action = request.form.get("action")  # 'increase' or 'decrease'
    cart = get_cart()
    key = str(item_id)

    if key in cart:
        if action == "increase":
            cart[key] += 1
        elif action == "decrease":
            cart[key] -= 1
            if cart[key] <= 0:
                del cart[key]
        session.modified = True

    return redirect(url_for("cart"))


# Customer Profile
@app.route("/profile")
@login_required
def profile():
    user = User.query.get_or_404(session["user_id"])
    return render_template("profile.html")

@app.route("/admin/profile")
@admin_required
def admin_profile():
    user = User.query.get_or_404(session["user_id"])
    return render_template("admin_profile.html")


# Track Order
@app.route("/track")
@login_required
def track():
    return render_template("track.html")


# admin pages

# admin home
@app.route("/admin/home")
@admin_required
def admin_home():
    return render_template("admin_home.html")

# admin menu
@app.route("/admin/menu")
@admin_required
def admin_menu():
    items = MenuItem.query.order_by(MenuItem.category, MenuItem.name).all()
    return render_template("admin_menu.html", items=items)

# admin reports
@app.route("/admin/reports")
@admin_required
def admin_reports():
    return render_template("admin_reports.html")

# checkout
@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart = get_cart()
    if not cart:
        flash("Your cart is empty.", "error")
        return redirect(url_for("menu"))

    # Only offer slots for today and the next 3 days.
    today = date.today()
    upcoming_dates = [today + timedelta(days=i) for i in range(4)]
    slots = (
        PickupSlot.query.filter(PickupSlot.slot_date.in_(upcoming_dates), PickupSlot.is_active.is_(True))
        .order_by(PickupSlot.slot_date, PickupSlot.id)
        .all()
    )

    if request.method == "POST":
        slot_id = request.form.get("pickup_slot_id")
        if not slot_id:
            flash("Please select a pickup time slot.", "error")
            return render_template("checkout.html", slots=slots, today=today)

        slot = PickupSlot.query.get(int(slot_id))
        if slot is None:
            flash("That pickup slot no longer exists.", "error")
            return render_template("checkout.html", slots=slots, today=today)

        # Check the slot isn't already full.
        if slot.current_booking_count() >= MAX_BOOKINGS_PER_SLOT:
            flash("Sorry, that pickup window just filled up. Please choose another.", "error")
            return render_template("checkout.html", slots=slots, today=today)

        # Build the order.
        order = Order(customer_id=session["user_id"], pickup_slot_id=slot.id)
        db.session.add(order)

        for item_id_str, qty in cart.items():
            item = MenuItem.query.get(int(item_id_str))
            if item is None or qty <= 0:
                continue
            order.items.append(
                OrderItem(menu_item_id=item.id, item_name=item.name, quantity=qty, unit_price=item.price)
            )

        order.calculate_total_amount()
        db.session.commit()

        # Empty the cart now that the order has been placed.
        session["cart"] = {}
        session.modified = True

        customer = User.query.get(session["user_id"])

        # send email place here

        flash("Order placed! Track its progress below.", "success")
        return redirect(url_for("track_order", order_id=order.id))

    return render_template("checkout.html", slots=slots, today=today)

#track order
@app.route("/track/<int:order_id>")
@login_required
def track_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.customer_id != session["user_id"]:
        flash("You don't have access to that order.", "error")
        return redirect(url_for("menu"))

    payment_info = {
        "payid": PAYID,
        "bank_name": BANK_NAME,
        "account_name": BANK_ACCOUNT_NAME,
        "bsb": BANK_BSB,
        "account_number": BANK_ACCOUNT_NUMBER,
    }
    return render_template("track.html", order=order, payment_info=payment_info)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        
        from seed import run_seed_if_empty
        run_seed_if_empty()
    app.run(debug=True, port=5000)