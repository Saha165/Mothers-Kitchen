import random
from datetime import datetime, timedelta

from app import app
from models import (
    Expense,
    MenuItem,
    Order,
    OrderItem,
    PickupSlot,
    User,
    db,
)

random.seed(42)  # reproducible dataset

DEMO_PASSWORD = "Customer@123"

DEMO_CUSTOMERS = [
    ("Priya Sharma", "priya.sharma@example.com", "0410 000 001"),
    ("Liam Thompson", "liam.thompson@example.com", "0410 000 002"),
    ("Aisha Khan", "aisha.khan@example.com", "0410 000 003"),
    ("Noah Williams", "noah.williams@example.com", "0410 000 004"),
    ("Ananya Iyer", "ananya.iyer@example.com", "0410 000 005"),
    ("Jack Robinson", "jack.robinson@example.com", "0410 000 006"),
    ("Meera Patel", "meera.patel@example.com", "0410 000 007"),
    ("Charlotte Nguyen", "charlotte.nguyen@example.com", "0410 000 008"),
    ("Ravi Kumar", "ravi.kumar@example.com", "0410 000 009"),
    ("Olivia Chen", "olivia.chen@example.com", "0410 000 010"),
    ("Arjun Singh", "arjun.singh@example.com", "0410 000 011"),
    ("Sophie Anderson", "sophie.anderson@example.com", "0410 000 012"),
    ("Divya Reddy", "divya.reddy@example.com", "0410 000 013"),
    ("Ethan Walker", "ethan.walker@example.com", "0410 000 014"),
    ("Fatima Hussain", "fatima.hussain@example.com", "0410 000 015"),
]

MONTHS_OF_HISTORY = 5
ORDERS_PER_CUSTOMER_RANGE = (18, 32)

PICKUP_SLOT_LABELS = [
    "11:00 AM - 11:30 AM",
    "11:30 AM - 12:00 PM",
    "12:00 PM - 12:30 PM",
    "12:30 PM - 1:00 PM",
    "5:30 PM - 6:00 PM",
    "6:00 PM - 6:30 PM",
    "6:30 PM - 7:00 PM",
]

EXPENSE_TEMPLATE_ITEMS = [
    ("Bulk Spices & Dairy Restock", "Ingredients & Stock", (180.0, 420.0)),
    ("Takeaway Containers & Bags", "Packaging & Containers", (75.0, 180.0)),
    ("Kitchen Electricity & Gas", "Utilities", (210.0, 360.0)),
    ("Equipment Servicing & Repairs", "Maintenance", (60.0, 150.0)),
    ("Local Marketing & Print Ads", "Marketing", (45.0, 110.0)),
    ("Fresh Vegetables & Meat", "Ingredients & Stock", (120.0, 290.0)),
]


def get_or_create_pickup_slot(order_date, slot_cache):
  label = random.choice(PICKUP_SLOT_LABELS)
  key = (order_date, label)
  if key in slot_cache:
    return slot_cache[key]

  slot = PickupSlot.query.filter_by(
      slot_date=order_date, slot_label=label
  ).first()
  if slot is None:
    slot = PickupSlot(slot_label=label, slot_date=order_date, max_capacity=5)
    db.session.add(slot)
    db.session.flush()
  slot_cache[key] = slot
  return slot


def run():
  with app.app_context():
    db.create_all()
    if User.query.filter_by(email=DEMO_CUSTOMERS[0][1]).first():
      print(
          "Demo dataset already present -- skipping.\n"
          "(Delete instance/mothers_kitchen.db and run `python app.py` "
          "then this script again to regenerate from scratch.)"
      )
      return

    menu_items = MenuItem.query.all()
    if not menu_items:
      print(
          "No menu items found. Run `python app.py` once first so the "
          "base seed data exists, then re-run this script."
      )
      return

    # --- Create Demo Customers -------------------------------------------
    customers = []
    for name, email, mobile in DEMO_CUSTOMERS:
      user = User(
          name=name,
          email=email,
          mobile_number=mobile,
          account_type="customer",
      )
      user.set_password(DEMO_PASSWORD)
      db.session.add(user)
      customers.append(user)
    db.session.flush()

    now = datetime.utcnow()
    slot_cache = {}
    total_orders_created = 0

    # --- Generate Orders ------------------------------------------------
    for customer in customers:
      num_orders = random.randint(*ORDERS_PER_CUSTOMER_RANGE)
      for _ in range(num_orders):
        days_ago = random.randint(0, MONTHS_OF_HISTORY * 30 - 1)
        order_dt = now - timedelta(
            days=days_ago,
            hours=random.randint(0, 10),
            minutes=random.randint(0, 59),
        )
        order_date = order_dt.date()

        slot = get_or_create_pickup_slot(order_date, slot_cache)

        if days_ago <= 3:
          status_step = random.choices([0, 1, 2, 3], weights=[10, 15, 15, 60])[
              0
          ]
        else:
          status_step = 3

        if status_step == 3:
          payment_status = "Paid"
        else:
          payment_status = random.choices(
              ["Paid", "Unpaid"], weights=[70, 30]
          )[0]

        order = Order(
            customer_id=customer.id,
            pickup_slot_id=slot.id,
            status_step=status_step,
            payment_status=payment_status,
            created_at=order_dt,
        )
        db.session.add(order)
        db.session.flush()

        num_items = random.randint(1, 4)
        chosen_items = random.sample(
            menu_items, k=min(num_items, len(menu_items))
        )

        order_total = 0.0
        for menu_item in chosen_items:
          qty = random.randint(1, 3)
          is_cancelled = random.random() < 0.03

          db.session.add(
              OrderItem(
                  order_id=order.id,
                  menu_item_id=menu_item.id,
                  item_name=menu_item.name,
                  quantity=qty,
                  unit_price=menu_item.price,
                  is_cancelled=is_cancelled,
              )
          )
          if not is_cancelled:
            order_total += qty * menu_item.price

        order.total_price = round(order_total, 2)
        total_orders_created += 1

    # --- Generate Historical Business Expenses --------------------------
    total_expenses_amount = 0.0
    total_expenses_count = 0

    for days_ago in range(0, MONTHS_OF_HISTORY * 30, 5):  # Every 5 days
      exp_date = (
          now - timedelta(days=days_ago, hours=random.randint(1, 8))
      ).date()
      for title, category, price_range in random.sample(
          EXPENSE_TEMPLATE_ITEMS, k=random.randint(1, 2)
      ):
        amount = round(random.uniform(*price_range), 2)
        expense = Expense(
            title=title,
            category=category,
            amount=amount,
            expense_date=exp_date,
            notes=f"Simulated operational expense for {exp_date.strftime('%b %Y')}",
        )
        db.session.add(expense)
        total_expenses_amount += amount
        total_expenses_count += 1

    # Commit all orders and expenses together
    db.session.commit()

    print(
        f"Created {len(customers)} demo customers, {total_orders_created} historical orders, "
        f"and {total_expenses_count} expense entries (${total_expenses_amount:,.2f} total) "
        f"spanning the last {MONTHS_OF_HISTORY} months.\n"
    )
    print(f"{'Customer ID':<12}{'Name':<20}{'Email':<32}{'Password'}")
    for c in customers:
      print(f"{c.id:<12}{c.name:<20}{c.email:<32}{DEMO_PASSWORD}")


if __name__ == "__main__":
  run()