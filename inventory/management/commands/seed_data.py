"""
Management command to seed the database with sample airsoft products,
categories, orders, and stock movements.

Usage:
    python manage.py seed_data
    python manage.py seed_data --clear   (wipe existing inventory data first)
"""
import urllib.request
import urllib.error

from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.contrib.auth.models import User
from inventory.models import Category, Product, Order, OrderItem, StockMovement

CATEGORIES = [
    {"name": "Rifles",       "slug": "rifles",       "description": "AEG, bolt-action, and HPA airsoft rifles"},
    {"name": "Pistols",      "slug": "pistols",      "description": "Gas and electric airsoft handguns"},
    {"name": "Tactical Gear","slug": "tactical-gear","description": "Vests, helmets, gloves and protective equipment"},
    {"name": "Ammunition",   "slug": "ammunition",   "description": "BB pellets in various weights and materials"},
    {"name": "Accessories",  "slug": "accessories",  "description": "Scopes, suppressors, grips, and upgrades"},
]

# picsum.photos/seed/<seed>/<w>/<h> returns a consistent, royalty-free placeholder image
PRODUCTS = [
    {
        "name": "AEG M4 Carbine",
        "slug": "aeg-m4-carbine",
        "sku": "RIF-001",
        "category": "Rifles",
        "description": "Full-metal AEG M4 Carbine with RIS handguard. Ideal for CQB and open-field engagements. Features a full-length Picatinny rail system and adjustable hop-up.",
        "price": "189.99",
        "stock": 15,
        "low_stock": 3,
        "image_seed": "m4carbine",
    },
    {
        "name": "AK-74 AEG",
        "slug": "ak-74-aeg",
        "sku": "RIF-002",
        "category": "Rifles",
        "description": "Classic AK-74 AEG with wood-style furniture. Reliable and accurate with a full-metal gearbox.",
        "price": "159.99",
        "stock": 8,
        "low_stock": 3,
        "image_seed": "ak74rifle",
    },
    {
        "name": "Glock 17 GBB",
        "slug": "glock-17-gbb",
        "sku": "PST-001",
        "category": "Pistols",
        "description": "Gas blowback Glock 17 replica. Full-metal slide with realistic recoil and blowback action. Compatible with standard Glock mags.",
        "price": "89.99",
        "stock": 20,
        "low_stock": 5,
        "image_seed": "glock17pistol",
    },
    {
        "name": "Desert Eagle GBB",
        "slug": "desert-eagle-gbb",
        "sku": "PST-002",
        "category": "Pistols",
        "description": "Iconic Desert Eagle gas blowback pistol. Heavyweight metal construction with powerful blowback and impressive range.",
        "price": "79.99",
        "stock": 4,
        "low_stock": 5,
        "image_seed": "deserteagle",
    },
    {
        "name": "MOLLE Tactical Vest",
        "slug": "molle-tactical-vest",
        "sku": "GEA-001",
        "category": "Tactical Gear",
        "description": "Adjustable MOLLE plate carrier vest with multiple magazine pouches. Compatible with all standard MOLLE attachments. One-size-fits-most design.",
        "price": "64.99",
        "stock": 18,
        "low_stock": 4,
        "image_seed": "tacticalvest",
    },
    {
        "name": "FAST Ballistic Helmet",
        "slug": "fast-ballistic-helmet",
        "sku": "GEA-002",
        "category": "Tactical Gear",
        "description": "High-cut FAST style airsoft helmet with NVG mount, side rails, and adjustable retention system. Lightweight ABS shell.",
        "price": "44.99",
        "stock": 7,
        "low_stock": 5,
        "image_seed": "tacticalhelmet",
    },
    {
        "name": "Bio 0.20g BBs — 5000pcs",
        "slug": "bio-020g-bbs-5000",
        "sku": "AMM-001",
        "category": "Ammunition",
        "description": "Premium biodegradable 0.20g BBs. Perfectly round with seamless polish for optimal accuracy. Suitable for AEGs and spring guns.",
        "price": "12.99",
        "stock": 50,
        "low_stock": 10,
        "image_seed": "airsoftbbs",
    },
    {
        "name": "0.25g Precision BBs — 3000pcs",
        "slug": "025g-precision-bbs-3000",
        "sku": "AMM-002",
        "category": "Ammunition",
        "description": "High-precision 0.25g polished BBs designed for upgraded AEGs and sniper rifles. Extra smooth surface for consistent hop-up performance.",
        "price": "14.99",
        "stock": 35,
        "low_stock": 10,
        "image_seed": "precisionbbs",
    },
    {
        "name": "Red Dot Reflex Sight",
        "slug": "red-dot-reflex-sight",
        "sku": "ACC-001",
        "category": "Accessories",
        "description": "Compact reflex red dot sight with 4 brightness settings. Fits all 20mm Picatinny and Weaver rails. Shockproof and fog-resistant.",
        "price": "34.99",
        "stock": 14,
        "low_stock": 4,
        "image_seed": "reddotsight",
    },
    {
        "name": "14mm CCW Suppressor",
        "slug": "14mm-ccw-suppressor",
        "sku": "ACC-002",
        "category": "Accessories",
        "description": "Aluminium 14mm counter-clockwise threaded suppressor mock. Reduces sound signature and adds a tactical look. 130mm length.",
        "price": "24.99",
        "stock": 22,
        "low_stock": 5,
        "image_seed": "suppressor",
    },
]

ORDERS = [
    {
        "customer_name": "John Rivera",
        "customer_email": "john.rivera@example.com",
        "status": "pending",
        "items": [("RIF-001", 1), ("ACC-001", 1)],
    },
    {
        "customer_name": "Sarah Chen",
        "customer_email": "sarah.chen@example.com",
        "status": "shipped",
        "items": [("PST-001", 2)],
    },
    {
        "customer_name": "Mike Torres",
        "customer_email": "mike.torres@example.com",
        "status": "delivered",
        "items": [("GEA-001", 1), ("AMM-001", 3), ("ACC-002", 1)],
    },
    {
        "customer_name": "Lisa Park",
        "customer_email": "lisa.park@example.com",
        "status": "confirmed",
        "items": [("RIF-002", 1), ("GEA-002", 1), ("AMM-002", 2)],
    },
]


def download_image(seed, width=600, height=400):
    """Download a placeholder image from picsum.photos using a named seed."""
    url = f"https://picsum.photos/seed/{seed}/{width}/{height}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        return None


class Command(BaseCommand):
    help = "Seed the database with sample airsoft products, orders, and stock movements"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing inventory data before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write(self.style.WARNING("Clearing existing inventory data..."))
            StockMovement.objects.all().delete()
            OrderItem.objects.all().delete()
            Order.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Cleared.\n"))

        admin_user = User.objects.filter(is_superuser=True).first()

        # --- Categories ---
        self.stdout.write("Creating categories...")
        cat_map = {}
        for data in CATEGORIES:
            cat, created = Category.objects.get_or_create(
                slug=data["slug"],
                defaults={"name": data["name"], "description": data["description"]},
            )
            cat_map[data["name"]] = cat
            status = "created" if created else "exists"
            self.stdout.write(f"  {cat.name} ({status})")

        # --- Products ---
        self.stdout.write("\nCreating products and downloading images...")
        product_map = {}
        for data in PRODUCTS:
            product, created = Product.objects.get_or_create(
                sku=data["sku"],
                defaults={
                    "name": data["name"],
                    "slug": data["slug"],
                    "category": cat_map[data["category"]],
                    "description": data["description"],
                    "price": data["price"],
                    "stock_quantity": data["stock"],
                    "low_stock_threshold": data["low_stock"],
                    "is_active": True,
                },
            )
            product_map[data["sku"]] = product

            if created:
                # Download and attach image
                self.stdout.write(f"  Downloading image for: {product.name} ...", ending="")
                image_data = download_image(data["image_seed"])
                if image_data:
                    product.image.save(f"{data['slug']}.jpg", ContentFile(image_data), save=True)
                    self.stdout.write(self.style.SUCCESS(" done"))
                else:
                    self.stdout.write(self.style.WARNING(" skipped (network error)"))
            else:
                self.stdout.write(f"  {product.name} (already exists)")

        # --- Stock Movements (initial restocks) ---
        self.stdout.write("\nLogging initial stock movements...")
        for sku, product in product_map.items():
            if not StockMovement.objects.filter(product=product, reason="purchase").exists():
                StockMovement.objects.create(
                    product=product,
                    reason="purchase",
                    quantity_change=product.stock_quantity,
                    notes="Initial stock loaded via seed_data command",
                    performed_by=admin_user,
                )
        self.stdout.write(self.style.SUCCESS("  Done"))

        # --- Orders ---
        self.stdout.write("\nCreating sample orders...")
        for order_data in ORDERS:
            if Order.objects.filter(customer_email=order_data["customer_email"]).exists():
                self.stdout.write(f"  Order for {order_data['customer_name']} already exists")
                continue

            order = Order.objects.create(
                customer_name=order_data["customer_name"],
                customer_email=order_data["customer_email"],
                status=order_data["status"],
            )
            for sku, qty in order_data["items"]:
                product = product_map.get(sku)
                if product:
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=qty,
                        unit_price=product.price,
                    )
            order.recalculate_total()
            self.stdout.write(f"  Order #{order.pk} — {order.customer_name} ({order.status}) ${order.total_price}")

        self.stdout.write("\n" + self.style.SUCCESS("=" * 50))
        self.stdout.write(self.style.SUCCESS("Seed complete!"))
        self.stdout.write(self.style.SUCCESS(f"  {len(CATEGORIES)} categories"))
        self.stdout.write(self.style.SUCCESS(f"  {len(PRODUCTS)} products"))
        self.stdout.write(self.style.SUCCESS(f"  {len(ORDERS)} orders"))
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write("\nVisit: http://127.0.0.1:8000/ to see the storefront")
        self.stdout.write("Admin:  http://127.0.0.1:8000/admin/\n")
