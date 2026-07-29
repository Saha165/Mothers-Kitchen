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

