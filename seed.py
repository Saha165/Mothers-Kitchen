from datetime import date, timedelta

from models import MenuItem, User, db

def run_seed_if_empty():
    if User.query.first() is not None:
        return

    # Demo admin account
    admin = User(
        name="Kitchen Admin",
        email="admin@motherskitchen.example",
        mobile_number="555-0100",
        account_type="admin",
    )
    admin.set_password("Admin@1234")
    db.session.add(admin)

    # Demo customer account
    demo_customer = User(
        name="Jamie",
        email="jamie@example.com",
        mobile_number="555-0101",
        account_type="customer",
    )
    demo_customer.set_password("Customer@123")
    db.session.add(demo_customer)

    db.session.commit()
    print(
        "Seed data created: 1 admin, 1 demo customer, "
    )



if __name__ == "__main__":
    from app import app

    with app.app_context():
        db.create_all()
        run_seed_if_empty()
