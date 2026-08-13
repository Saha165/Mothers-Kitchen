import os
import re
import threading
import uuid
import calendar
from datetime import date, datetime, timedelta
from functools import wraps

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from models import MenuItem, Order, OrderItem, PickupSlot, User, db, Expense


app = Flask(__name__)
app.secret_key = "mothers_kitchen_secret_key"

# Database Configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")

# Create instance directory if it doesn't exist
os.makedirs(INSTANCE_DIR, exist_ok=True)

# Point SQLAlchemy directly inside the instance folder
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(INSTANCE_DIR, 'mothers_kitchen.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "images", "menu")
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}    

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

# Admin required function
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

# Images
def save_menu_image(file_storage):
    # Saves an uploaded photo and returns its new URL, or None if no file was given
    if not file_storage or file_storage.filename == "":
        return None

    extension = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Unsupported file type. Please upload a PNG, JPG, JPEG, GIF, or WEBP image.")

    # Add a random prefix so two people uploading images with same name don't overwrite each other
    unique_name = f"{uuid.uuid4().hex}_{secure_filename(file_storage.filename)}"
    file_storage.save(os.path.join(UPLOAD_FOLDER, unique_name))
    return f"/static/images/menu/{unique_name}"


def delete_menu_image(image_url):
    # Deletes a previously uploaded photo file, if this URL points to one
    if not image_url or not image_url.startswith("/static/images/menu/"):
        return  # It's an external URL (or empty) -- nothing to delete.
    file_path = os.path.join(UPLOAD_FOLDER, image_url.rsplit("/", 1)[-1])
    if os.path.isfile(file_path):
        os.remove(file_path)


# Home Route
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

# Customer pages
# Customer menu
@app.route("/menu")
@login_required
def menu():
    # Shows every available dish. Supports a search box and dietary filters
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

# Customer menu item
@app.route("/menu/<int:item_id>")
@login_required
def item_detail(item_id):
    item = MenuItem.query.get_or_404(item_id)
    return render_template("item_detail.html", item=item)

# Cart
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

# Add to cart
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

# Remove form cart
@app.route("/cart/remove/<int:item_id>", methods=["POST"])
@login_required
def remove_from_cart(item_id):
    cart = get_cart()
    cart.pop(str(item_id), None)
    session.modified = True
    flash("Item removed from cart.", "success")
    return redirect(url_for("cart"))

# Update cart
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
    orders = Order.query.filter_by(customer_id=user.id).order_by(Order.created_at.desc()).all()
    return render_template("profile.html", user=user, orders=orders)


# Track order
@app.route("/track")
@app.route("/track/<int:order_id>")
@login_required
def track(order_id=None):
    if order_id is None:
        latest_order = (
            Order.query.filter_by(customer_id=session["user_id"])
            .order_by(Order.created_at.desc())
            .first()
        )
        if not latest_order:
            flash("You have no active orders to track.", "error")
            return redirect(url_for("menu"))
        order_id = latest_order.id

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

@app.route("/api/order/<int:order_id>/status")
def api_order_status(order_id):
    # Polled every few seconds by track.html to animate the progress bar
    order = Order.query.get_or_404(order_id)

    if session.get("account_type") != "admin" and order.customer_id != session.get("user_id"):
        return jsonify({"error": "forbidden"}), 403

    return jsonify({
        "order_id": order.id,
        "status_step": order.status_step,
        "status_label": order.status_label(),
        "total_steps": len(Order.STATUS_LABELS),
    })

# Checkout
@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart = get_cart()
    if not cart:
        flash("Your cart is empty.", "error")
        return redirect(url_for("menu"))

    # Only offer slots for today and the next 7 days
    today = date.today()
    upcoming_dates = [today + timedelta(days=i) for i in range(8)]
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

        # Check the slot isn't already full
        if slot.current_booking_count() >= MAX_BOOKINGS_PER_SLOT:
            flash("Sorry, that pickup window just filled up. Please choose another.", "error")
            return render_template("checkout.html", slots=slots, today=today)

        # Build the order
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

        # Empty the cart now that the order has been placed
        session["cart"] = {}
        session.modified = True

        customer = User.query.get(session["user_id"])

        flash("Order placed! Track its progress below.", "success")
        return redirect(url_for("track", order_id=order.id))

    return render_template("checkout.html", slots=slots, today=today)

@app.route("/api/slots")
def api_slot_availability():
    # Lets checkout.html grey out full pickup windows without reloading the page
    slots = PickupSlot.query.filter_by(is_active=True).all()
    payload = []
    for slot in slots:
        count = slot.current_booking_count()
        payload.append({
            "id": slot.id, "date": slot.slot_date.isoformat(), "label": slot.slot_label,
            "booked": count, "capacity": slot.max_capacity, "is_full": count >= slot.max_capacity,
        })
    return jsonify(payload)



# Admin pages
# Admin home
@app.route("/admin/home")
@admin_required
def admin_home():
    return render_template("admin_home.html")

# Admin profile
@app.route("/admin/profile")
@admin_required
def admin_profile():
    user = User.query.get_or_404(session["user_id"])
    return render_template("admin_profile.html", user=user)

# Admin menu
@app.route("/admin/menu")
@admin_required
def admin_menu():
    items = MenuItem.query.order_by(MenuItem.category, MenuItem.name).all()
    return render_template("admin_menu.html", items=items)


@app.route("/admin/menu/<int:item_id>/toggle", methods=["POST"])
@admin_required
def admin_toggle_availability(item_id):
    item = MenuItem.query.get_or_404(item_id)
    item.is_available = not item.is_available
    db.session.commit()
    state = "available" if item.is_available else "sold out"
    flash(f"{item.name} is now marked as {state}.", "success")
    return redirect(url_for("admin_menu"))


@app.route("/admin/menu/add", methods=["GET", "POST"])
@admin_required
def admin_add_menu_item():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        price = request.form.get("price", type=float)
        category = request.form.get("category", "Main").strip()
        image_url = request.form.get("image_url", "").strip()

        # An uploaded file always wins over a typed-in URL
        try:
            uploaded_url = save_menu_image(request.files.get("image_file"))
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("admin_menu_form.html", item=None)

        if uploaded_url:
            image_url = uploaded_url

        if not name or not description or price is None or not image_url:
            flash("Name, description, price, and either a photo upload or photo URL are required.", "error")
            return render_template("admin_menu_form.html", item=None)

        if price <= 0:
            flash("Price must be greater than $0.", "error")
            return render_template("admin_menu_form.html", item=None)

        item = MenuItem(
            name=name,
            description=description,
            price=price,
            category=category or "Main",
            image_url=image_url,
            is_vegan=bool(request.form.get("is_vegan")),
            is_gluten_free=bool(request.form.get("is_gluten_free")),
            is_dairy_free=bool(request.form.get("is_dairy_free")),
            is_nut_free=bool(request.form.get("is_nut_free")),
        )
        db.session.add(item)
        db.session.commit()
        flash(f"{item.name} added to the menu.", "success")
        return redirect(url_for("admin_menu"))

    return render_template("admin_menu_form.html", item=None)


@app.route("/admin/menu/<int:item_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_menu_item(item_id):
    item = MenuItem.query.get_or_404(item_id)

    if request.method == "POST":
        item.name = request.form.get("name", item.name).strip()
        item.description = request.form.get("description", item.description).strip()
        price = request.form.get("price", type=float)
        if price is not None and price > 0:
            item.price = price
        item.category = request.form.get("category", item.category).strip()

        try:
            uploaded_url = save_menu_image(request.files.get("image_file"))
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("admin_menu_form.html", item=item)

        image_url = request.form.get("image_url", "").strip()
        new_image_url = uploaded_url or image_url or None
        if new_image_url and new_image_url != item.image_url:
            delete_menu_image(item.image_url)  # Deletes the old photo if stored locally
            item.image_url = new_image_url


        item.is_vegan = bool(request.form.get("is_vegan"))
        item.is_gluten_free = bool(request.form.get("is_gluten_free"))
        item.is_dairy_free = bool(request.form.get("is_dairy_free"))
        item.is_nut_free = bool(request.form.get("is_nut_free"))

        db.session.commit()
        flash(f"{item.name} updated.", "success")
        return redirect(url_for("admin_menu"))

    return render_template("admin_menu_form.html", item=item)


@app.route("/admin/menu/<int:item_id>/delete", methods=["POST"])
@admin_required
def admin_delete_menu_item(item_id):
    item = MenuItem.query.get_or_404(item_id)
    delete_menu_image(item.image_url)
    db.session.delete(item)
    db.session.commit()
    flash(f"{item.name} removed from the menu.", "success")
    return redirect(url_for("admin_menu"))

# Admin reports
# Add expenses
@app.route("/admin/expenses/add", methods=["POST"])
@admin_required
def add_expense():
  # Handles form submission to add a new business expense
  description = request.form.get("description", "").strip()
  category = request.form.get("category", "General").strip()
  amount_str = request.form.get("amount", "0")
  expense_date_str = request.form.get("expense_date")

  if not description or not amount_str:
    flash("Please provide both a description and an amount.", "error")
    return redirect(url_for("admin_reports"))

  try:
    amount = float(amount_str)
    if amount <= 0:
      raise ValueError()
  except ValueError:
    flash("Please enter a valid positive expense amount.", "error")
    return redirect(url_for("admin_reports"))

  try:
    expense_date = (
        datetime.strptime(expense_date_str, "%Y-%m-%d").date()
        if expense_date_str
        else date.today()
    )
  except ValueError:
    expense_date = date.today()

  new_expense = Expense(
      description=description,
      category=category,
      amount=amount,
      expense_date=expense_date,
  )
  db.session.add(new_expense)
  db.session.commit()

  flash("Expense logged successfully!", "success")
  return redirect(url_for("admin_reports"))

# Delete expenses
@app.route("/admin/expenses/<int:expense_id>/delete", methods=["POST"])
@admin_required
def delete_expense(expense_id):
  # Deletes an expense entry from the database
  expense = Expense.query.get_or_404(expense_id)
  db.session.delete(expense)
  db.session.commit()
  flash("Expense record removed.", "info")
  return redirect(url_for("admin_reports"))

# Report
@app.route("/admin/reports")
@admin_required
def admin_reports():
  # Builds the Reports page with Revenue, Expense, and Net Profit analytics
  period = request.args.get("period", "week")
  if period not in ("week", "month", "year"):
    period = "week"

  selected_category = request.args.get("category", "all")

  now = datetime.utcnow()
  period_start = {
      "week": now - timedelta(days=7),
      "month": now - timedelta(days=30),
      "year": now - timedelta(days=365),
  }[period]
  period_start_date = period_start.date()
  period_label = {
      "week": "Last 7 Days",
      "month": "Last 30 Days",
      "year": "Last 12 Months",
  }[period]

  # All existing menu item categories
  all_categories = [
      row[0]
      for row in db.session.query(MenuItem.category)
      .distinct()
      .order_by(MenuItem.category)
      .all()
  ]

  menu_item_meta = {
      mi.id: {
          "name": mi.name,
          "category": mi.category,
          "is_available": mi.is_available,
      }
      for mi in MenuItem.query.all()
  }

  # Fetch all orders created in period
  all_orders_in_range = Order.query.filter(Order.created_at >= period_start).all()

  # Filter only PAID orders for financial calculations & revenue graphs
  orders_in_range = [
      o for o in all_orders_in_range if o.payment_status == "Paid"
  ]
  unpaid_orders = [o for o in all_orders_in_range if o.payment_status != "Paid"]

  order_ids = [o.id for o in orders_in_range]
  order_created_map = {o.id: o.created_at for o in orders_in_range}

  total_income = sum(o.total_price for o in orders_in_range)
  most_purchased_item = "N/A"
  category_totals = {}
  top_items_sorted = []
  item_perf = []
  qty_by_item_name = {}
  item_perf_acc = {}
  order_item_rows = []

  if order_ids:
    order_item_rows = OrderItem.query.filter(
        OrderItem.order_id.in_(order_ids), OrderItem.is_cancelled.is_(False)
    ).all()

    for oi in order_item_rows:
      meta = menu_item_meta.get(oi.menu_item_id, {})
      category = meta.get("category", "Uncategorised")
      is_available = meta.get("is_available", False)
      revenue = oi.quantity * oi.unit_price

      category_totals[category] = category_totals.get(category, 0.0) + revenue
      qty_by_item_name[oi.item_name] = (
          qty_by_item_name.get(oi.item_name, 0) + oi.quantity
      )

      acc = item_perf_acc.setdefault(
          oi.menu_item_id,
          {
              "name": oi.item_name,
              "category": category,
              "is_available": is_available,
              "qty": 0,
              "revenue": 0.0,
          },
      )
      acc["qty"] += oi.quantity
      acc["revenue"] += revenue

    category_totals = {k: round(v, 2) for k, v in category_totals.items()}
    top_items_sorted = sorted(
        qty_by_item_name.items(), key=lambda kv: kv[1], reverse=True
    )[:8]
    most_purchased_item = (
        top_items_sorted[0][0] if top_items_sorted else "N/A"
    )

    for acc in item_perf_acc.values():
      item_perf.append({
          "name": acc["name"],
          "category": acc["category"],
          "qty": acc["qty"],
          "revenue": round(acc["revenue"], 2),
          "is_available": acc["is_available"],
      })
    item_perf.sort(key=lambda r: r["revenue"], reverse=True)

  # Category detail drill-down
  category_detail = None
  if selected_category != "all":
    category_items = [
        row for row in item_perf if row["category"] == selected_category
    ]
    category_revenue = category_totals.get(selected_category, 0.0)
    category_detail = {
        "category": selected_category,
        "revenue": category_revenue,
        "qty": sum(row["qty"] for row in category_items),
        "pct_of_total": round(
            (category_revenue / total_income * 100) if total_income else 0, 1
        ),
        "line_items": category_items,
    }

  # Breakdown rows
  qty_by_category = {}
  for row in item_perf:
    qty_by_category[row["category"]] = (
        qty_by_category.get(row["category"], 0) + row["qty"]
    )

  breakdown_rows = [
      {
          "category": cat,
          "qty": qty_by_category.get(cat, 0),
          "revenue": revenue,
          "pct": round(
              (revenue / total_income * 100) if total_income else 0, 1
          ),
      }
      for cat, revenue in category_totals.items()
  ]
  breakdown_rows.sort(key=lambda r: r["revenue"], reverse=True)

  # Fetch Expenses for selected period
  expenses_in_range = Expense.query.filter(
      Expense.expense_date >= period_start_date
  ).all()
  total_expenses = sum(e.amount for e in expenses_in_range)
  net_profit = total_income - total_expenses

  recent_expenses = (
      Expense.query.order_by(Expense.expense_date.desc()).limit(15).all()
  )

  # Build Time Buckets for Charts
  if period in ("week", "month"):
    days_back = 6 if period == "week" else 29
    date_format = "%a %d/%m" if period == "week" else "%d/%m"
    bucket_keys = [
        (now - timedelta(days=i)).date() for i in range(days_back, -1, -1)
    ]
    trend_labels = [k.strftime(date_format) for k in bucket_keys]

    def bucket_key_for(dt):
      if isinstance(dt, datetime):
        return dt.date()
      return dt

  else:  # year -> 12 monthly buckets
    buckets = []
    y, m = now.year, now.month
    for i in range(11, -1, -1):
      bucket_m = m - i
      bucket_y = y
      while bucket_m <= 0:
        bucket_m += 12
        bucket_y -= 1
      buckets.append((bucket_y, bucket_m))
    bucket_keys = buckets
    trend_labels = [f"{calendar.month_abbr[bm]} {by}" for by, bm in buckets]

    def bucket_key_for(dt):
      return (dt.year, dt.month)

  key_to_index = {key: idx for idx, key in enumerate(bucket_keys)}

  # 1. Revenue trend values (Paid orders only)
  trend_values = [0.0] * len(bucket_keys)
  for o in orders_in_range:
    idx = key_to_index.get(bucket_key_for(o.created_at))
    if idx is not None:
      trend_values[idx] += o.total_price
  trend_values = [round(v, 2) for v in trend_values]

  # 2. Expense trend values
  expense_values = [0.0] * len(bucket_keys)
  for exp in expenses_in_range:
    idx = key_to_index.get(bucket_key_for(exp.expense_date))
    if idx is not None:
      expense_values[idx] += exp.amount
  expense_values = [round(v, 2) for v in expense_values]

  # 3. Net Profit trend values (Paid Revenue - Expenses)
  net_profit_values = [
      round(rev - exp, 2) for rev, exp in zip(trend_values, expense_values)
  ]

  # Category trend lines (Paid orders only)
  top_categories_for_trend = [
      cat
      for cat, _ in sorted(
          category_totals.items(), key=lambda kv: kv[1], reverse=True
      )
  ][:5]
  category_trend = {
      cat: [0.0] * len(bucket_keys) for cat in top_categories_for_trend
  }

  if order_ids and top_categories_for_trend:
    for oi in order_item_rows:
      meta = menu_item_meta.get(oi.menu_item_id, {})
      cat = meta.get("category", "Uncategorised")
      if cat not in category_trend:
        continue
      order_dt = order_created_map.get(oi.order_id)
      if order_dt is None:
        continue
      idx = key_to_index.get(bucket_key_for(order_dt))
      if idx is not None:
        category_trend[cat][idx] += oi.quantity * oi.unit_price

  category_trend = {
      cat: [round(v, 2) for v in values]
      for cat, values in category_trend.items()
  }

  # Paid / Unpaid totals for doughnut chart
  paid_total = round(sum(o.total_price for o in orders_in_range), 2)
  unpaid_total = round(sum(o.total_price for o in unpaid_orders), 2)

  # Monthly Trailing 12-Month Financial Summary (Paid orders only)
  year_start = now - timedelta(days=365)
  orders_last_year = Order.query.filter(
      Order.created_at >= year_start, Order.payment_status == "Paid"
  ).all()
  expenses_last_year = Expense.query.filter(
      Expense.expense_date >= year_start.date()
  ).all()

  monthly_pl = []
  y, m = now.year, now.month
  for i in range(11, -1, -1):
    bucket_m = m - i
    bucket_y = y
    while bucket_m <= 0:
      bucket_m += 12
      bucket_y -= 1

    m_orders = [
        o
        for o in orders_last_year
        if o.created_at.year == bucket_y and o.created_at.month == bucket_m
    ]
    m_expenses = [
        e
        for e in expenses_last_year
        if e.expense_date.year == bucket_y and e.expense_date.month == bucket_m
    ]

    m_income = sum(o.total_price for o in m_orders)
    m_expense_total = sum(e.amount for e in m_expenses)
    m_net = m_income - m_expense_total

    monthly_pl.append({
        "month": f"{calendar.month_abbr[bucket_m]} {bucket_y}",
        "income": round(m_income, 2),
        "expenses": round(m_expense_total, 2),
        "net_profit": round(m_net, 2),
    })

  item_perf_chart = item_perf[:10]

  return render_template(
      "admin_reports.html",
      period=period,
      period_label=period_label,
      selected_category=selected_category,
      all_categories=all_categories,
      category_detail=category_detail,
      total_income=round(total_income, 2),
      total_expenses=round(total_expenses, 2),
      net_profit=round(net_profit, 2),
      most_purchased_item=most_purchased_item,
      order_count=len(orders_in_range),
      trend_labels=trend_labels,
      trend_values=trend_values,
      expense_values=expense_values,
      net_profit_values=net_profit_values,
      category_labels=list(category_totals.keys()),
      category_values=list(category_totals.values()),
      category_trend=category_trend,
      top_items_labels=[row[0] for row in top_items_sorted],
      top_items_values=[row[1] for row in top_items_sorted],
      paid_total=paid_total,
      unpaid_total=unpaid_total,
      breakdown_rows=breakdown_rows,
      item_perf=item_perf,
      item_perf_chart=item_perf_chart,
      monthly_pl=monthly_pl,
      recent_expenses=recent_expenses,
  )

# Admin View Orders
@app.route("/admin/orders")
@admin_required
def admin_orders():
    # Shows every order that hasn't been picked up yet, earliest pickup date first
    orders = (
        Order.query.join(PickupSlot)
        .filter(Order.status_step < 3)
        .order_by(PickupSlot.slot_date.asc(), PickupSlot.id.asc())
        .all()
    )
    completed_orders = (
        Order.query.filter(Order.status_step == 3)
        .order_by(Order.created_at.desc())
        .limit(20)
        .all()
    )
    return render_template("admin_orders.html", orders=orders, completed_orders=completed_orders)


@app.route("/admin/order/<int:order_id>/payment", methods=["POST"])
@admin_required
def admin_toggle_payment_status(order_id):
    # Flips an order between Paid and Unpaid
    order = Order.query.get_or_404(order_id)
    order.payment_status = "Paid" if order.payment_status != "Paid" else "Unpaid"
    db.session.commit()
    flash(f"Order #{order.id} marked as {order.payment_status}.", "success")
    return redirect(url_for("admin_orders"))


@app.route("/admin/order/<int:order_id>/status", methods=["POST"])
@admin_required
def admin_update_order_status(order_id):
    # Moves an order to a new milestone (Accepted / Preparing / Ready / Picked Up)
    order = Order.query.get_or_404(order_id)
    new_step = request.form.get("status_step", type=int)

    if new_step is None:
        flash("Invalid status update.", "error")
        return redirect(url_for("admin_orders"))

    final_step = len(Order.STATUS_LABELS) - 1

    # Don't allow "Picked Up" until the order has been marked Paid.
    if new_step == final_step and order.payment_status != "Paid":
        flash(
            f"Order #{order.id} is still marked Unpaid. Please confirm the "
            "bank transfer / PayID payment before marking it as Picked Up.",
            "error",
        )
        return redirect(url_for("admin_orders"))

    previous_step = order.status_step
    order.update_status(new_step)
    db.session.commit()

    customer = User.query.get(order.customer_id)
    
    flash(f"Order #{order.id} updated to '{order.status_label()}'.", "success")
    return redirect(url_for("admin_orders"))

@app.route("/admin/order/<int:order_id>/item/<int:item_id>/cancel", methods=["POST"])
@admin_required
def admin_toggle_item_cancellation(order_id, item_id):

    # Removes (or restores) ONE dish from an order, e.g. because it sold out
    # Updates the order total, adjusts inventory, toggles dish availability

    order = Order.query.get_or_404(order_id)
    item = OrderItem.query.filter_by(id=item_id, order_id=order.id).first_or_404()
    customer = User.query.get(order.customer_id)

    item.is_cancelled = not item.is_cancelled

    # Ensure we grab the actual MenuItem record from the foreign key
    menu_item = MenuItem.query.get(item.menu_item_id)

    if item.is_cancelled:
        # Mark the dish as sold out on the menu so future customers can't order it
        if menu_item:
            menu_item.is_available = False

    else:
        # If restored, make the dish available on the menu again
        if menu_item:
            menu_item.is_available = True


    order.calculate_total_amount()
    db.session.commit()

    if item.is_cancelled:
        flash(f"'{item.item_name}' removed from Order #{order.id} and marked as Sold Out.", "success")
    else:
        flash(f"'{item.item_name}' restored to Order #{order.id}.", "success")

    return redirect(url_for("admin_menu"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        
        from seed import run_seed_if_empty
        run_seed_if_empty()
    app.run(debug=True, port=5000)