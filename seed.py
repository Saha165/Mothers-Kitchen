from datetime import date, timedelta

from models import MenuItem, User, db, PickupSlot

#Sample Menu Items
SAMPLE_MENU_ITEMS = [
    {
        "name": "Paneer Tikka Masala",
        "description": (
            "Chunks of grilled cottage cheese simmered in a rich, "
            "spiced tomato-cream gravy. Served with a side of basmati rice."
        ),
        "price": 12.99,
        "category": "Main Course",
        "image_url": "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=600&auto=format&fit=crop",

        "is_vegan": False,
        "is_gluten_free": True,
        "is_dairy_free": False,
        "is_nut_free": True,
    },
    {
        "name": "Chana Masala",
        "description": (
            "Chickpeas slow-cooked in a tangy onion-tomato masala with "
            "cumin, coriander, and a hint of garam masala. Naturally vegan."
        ),
        "price": 10.99,
        "category": "Main Course",
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTSLzSaXelnZPBdHpTUJ1mJODuIyplhkJJuleCeP-dIlQ&s=10",
        "is_vegan": True,
        "is_gluten_free": True,
        "is_dairy_free": True,
        "is_nut_free": True,
    },
    {
        "name": "Dal Tadka",
        "description": (
            "Yellow lentils simmered until creamy, finished with a "
            "sizzling tempering of ghee, cumin seeds, and dried red chili."
        ),
        "price": 9.49,
        "category": "Main Course",
        "image_url": "https://www.honeywhatscooking.com/wp-content/uploads/2025/09/Spinach-Dal-Fry-main.jpg",
        "is_vegan": False,
        "is_gluten_free": True,
        "is_dairy_free": False,
        "is_nut_free": True,
    },
    {
        "name": "Vegetable Samosas (3 pc)",
        "description": (
            "Crisp, golden pastry parcels filled with spiced potatoes "
            "and green peas. Served with tamarind and mint chutneys."
        ),
        "price": 6.99,
        "category": "Appetizer",
        "image_url": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&auto=format&fit=crop",
        "is_vegan": True,
        "is_gluten_free": False,
        "is_dairy_free": True,
        "is_nut_free": True,
    },
    {
        "name": "Garden Fresh Salad Bowl",
        "description": (
            "Crisp seasonal greens, cucumber, cherry tomatoes, and "
            "pickled onion tossed in a light lemon-herb dressing."
        ),
        "price": 7.99,
        "category": "Salad",
        "image_url": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&auto=format&fit=crop",
        "is_vegan": True,
        "is_gluten_free": True,
        "is_dairy_free": True,
        "is_nut_free": True,
    },
    {
        "name": "Garlic Naan",
        "description": (
            "Pillowy leavened flatbread brushed with garlic butter and "
            "baked fresh to order in a tandoor-style oven."
        ),
        "price": 3.49,
        "category": "Bread",
        "image_url": "https://manekancor.com/wp-content/uploads/2025/08/11-1.jpg",
        "is_vegan": False,
        "is_gluten_free": False,
        "is_dairy_free": False,
        "is_nut_free": True,
    },
    {
        "name": "Gulab Jamun (2 pc)",
        "description": (
            "Warm, soft milk-solid dumplings soaked in a light "
            "cardamom-rose sugar syrup. A classic, comforting dessert."
        ),
        "price": 4.99,
        "category": "Dessert",
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRia5aqgbfZ7MLvjqCPwxIK0vSxzOcrd4es7F7efte-zQ&s=10",
        "is_vegan": False,
        "is_gluten_free": False,
        "is_dairy_free": False,
        "is_nut_free": True,
    },
    {
            "name": "Vegetable Biryani",
            "description": (
                "Fragrant basmati rice layered with mixed seasonal vegetables, "
                "saffron, and whole spices, slow-cooked in the traditional dum style."
            ),
            "price": 11.49,
            "category": "Main Course",
            "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQF_EV-qh4Pu13muRkx4ElZUeOKOb7DLA3HNpUfLreGtA&s=10",
            "is_vegan": True,
            "is_gluten_free": True,
            "is_dairy_free": True,
            "is_nut_free": False,
        },
]

#slot labels
DAILY_SLOT_LABELS = [
    "11:00 AM - 11:30 AM",
    "11:30 AM - 12:00 PM",
    "12:00 PM - 12:30 PM",
    "12:30 PM - 1:00 PM",
    "5:30 PM - 6:00 PM",
    "6:00 PM - 6:30 PM",
    "6:30 PM - 7:00 PM",
]

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

    #Demo Menu Items
    menu_items_by_name = {}
    for item_data in SAMPLE_MENU_ITEMS:
        menu_item = MenuItem(**item_data)
        db.session.add(menu_item)
        menu_items_by_name[menu_item.name] = menu_item
    db.session.flush()

    #pickup slots
    today = date.today()
    for day_offset in range(14):
        slot_date = today + timedelta(days=day_offset)
        for label in DAILY_SLOT_LABELS:
            db.session.add(
                PickupSlot(slot_label=label, slot_date=slot_date, max_capacity=5)
            )

    db.session.commit()
    print(
        "Seed data created: 1 admin, 1 demo customer, "
        f"{len(SAMPLE_MENU_ITEMS)} menu items,"
    )



if __name__ == "__main__":
    from app import app

    with app.app_context():
        db.create_all()
        run_seed_if_empty()
