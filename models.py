from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(db.Model):
   
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    mobile_number = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    account_type = db.Column(db.String(20), nullable=False, default="customer")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw_password):
        # hashes the password
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        # checks the password
        return check_password_hash(self.password_hash, raw_password)


class MenuItem(db.Model):
    """One dish on the menu (Mother's Kitchen is entirely vegetarian)."""

    __tablename__ = "menu_items"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(60), nullable=False, default="Main")
    image_url = db.Column(db.String(500), nullable=False)

    # Dietary badges shown on the menu page filters.
    is_vegan = db.Column(db.Boolean, default=False, nullable=False)
    is_gluten_free = db.Column(db.Boolean, default=False, nullable=False)
    is_dairy_free = db.Column(db.Boolean, default=False, nullable=False)
    is_nut_free = db.Column(db.Boolean, default=False, nullable=False)

    # Admin can turn a dish off when it sells out.
    is_available = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PickupSlot(db.Model):
    """A bookable pickup time window, e.g. '12:00 PM - 12:30 PM'."""

    __tablename__ = "pickup_slots"

    id = db.Column(db.Integer, primary_key=True)
    slot_label = db.Column(db.String(60), nullable=False)
    slot_date = db.Column(db.Date, nullable=False)
    max_capacity = db.Column(db.Integer, nullable=False, default=5)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    orders = db.relationship("Order", backref="pickup_slot", lazy=True)

    def current_booking_count(self):
        """How many orders are already booked into this slot."""
        return Order.query.filter_by(pickup_slot_id=self.id).count()

class Order(db.Model):
    """
    One customer order. `status_step` tracks where the order is in its
    journey:  0 = Order Accepted, 1 = Preparing, 2 = Ready to Pick Up,
    3 = Picked Up (Completed).
    """

    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    pickup_slot_id = db.Column(db.Integer, db.ForeignKey("pickup_slots.id"), nullable=False)

    total_price = db.Column(db.Float, nullable=False, default=0.0)
    status_step = db.Column(db.Integer, nullable=False, default=0)

    STATUS_LABELS = [
        "Order Accepted",
        "Preparing Order",
        "Ready to Pick Up",
        "Picked Up (Completed)",
    ]

    # Mother's Kitchen is paid by bank transfer / PayID, not card, so an
    # admin marks this "Paid" by hand once the transfer arrives.
    payment_status = db.Column(db.String(20), nullable=False, default="Unpaid")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship("OrderItem", backref="order", lazy=True, cascade="all, delete-orphan")

    def status_label(self):
        """Turns the status_step number into a readable label."""
        return self.STATUS_LABELS[self.status_step]

    def payment_reference(self):
        """The reference number a customer quotes when they pay."""
        return f"MK-{self.id:05d}"

    def active_items(self):
        """The items still in this order (not cancelled by the admin)."""
        return [item for item in self.items if not item.is_cancelled]

    def cancelled_items(self):
        """Items the admin removed because a dish ran out, etc."""
        return [item for item in self.items if item.is_cancelled]

    def calculate_total_amount(self):
        """Adds up quantity * price for every non-cancelled item."""
        self.total_price = sum(item.subtotal() for item in self.active_items())
        return self.total_price

    def update_status(self, new_status_step):
        """Moves the order to a new step, keeping it a valid step number."""
        highest_step = len(self.STATUS_LABELS) - 1
        self.status_step = max(0, min(new_status_step, highest_step))

    def generate_order_summary(self):
        """A plain-text summary of the order, used inside emails."""
        lines = [f"Order #{self.id} - {self.status_label()}"]
        for item in self.items:
            note = " (cancelled - out of stock)" if item.is_cancelled else ""
            lines.append(f"  {item.quantity} x {item.item_name} = ${item.subtotal():.2f}{note}")
        lines.append(f"Total: ${self.total_price:.2f}")
        return "\n".join(lines)

class OrderItem(db.Model):
    """One dish within an order, e.g. '2 x Paneer Tikka Masala'."""

    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey("menu_items.id"), nullable=False)

    # We save the name and price at the time of ordering, so old orders
    # still look right even if the dish's name or price changes later.
    item_name = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)

    # True if the admin had to remove this one dish from the order
    # (e.g. it sold out) without cancelling the whole order.
    is_cancelled = db.Column(db.Boolean, nullable=False, default=False)

    def subtotal(self):
        return self.quantity * self.unit_price
