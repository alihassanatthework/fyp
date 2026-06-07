"""
scripts/seed_providers.py
─────────────────────────
Seeds the Provider table with realistic dermatologists and salons across
Lahore so the Bookings page has data to show during the demo.

Run:
    cd "/Users/alihassan/Desktop/fyp devlopment be"
    source venv/bin/activate
    python scripts/seed_providers.py
"""
import os
import sys
import django

# Ensure project root is on sys.path so 'config' module is importable.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from providers.models import Provider

from datetime import time as dt_time

PROVIDERS = [
    # ─── Dermatologists (Lahore) ────────────────────────────────────
    {"name": "Dr. Saira Ahmed — Skin & Laser Clinic",
     "provider_type": "dermatologist", "address": "Block J, Phase 1, DHA",
     "city": "Lahore", "phone": "+92 42 1234 5601",
     "latitude": 31.4690, "longitude": 74.4090,
     "opening_time": dt_time(10, 0), "closing_time": dt_time(19, 0), "working_days": "Mon-Sat"},
    {"name": "National Dermatology Centre",
     "provider_type": "dermatologist", "address": "21-K Gulberg III",
     "city": "Lahore", "phone": "+92 42 1234 5602",
     "latitude": 31.5135, "longitude": 74.3470,
     "opening_time": dt_time(9, 0), "closing_time": dt_time(21, 0), "working_days": "Mon-Sat"},
    {"name": "Dr. Imran Hussain — Acne & Hair Clinic",
     "provider_type": "dermatologist", "address": "Wapda Town Block H1",
     "city": "Lahore", "phone": "+92 42 1234 5603",
     "latitude": 31.4242, "longitude": 74.3055,
     "opening_time": dt_time(11, 0), "closing_time": dt_time(20, 0), "working_days": "Tue-Sun"},
    {"name": "Skin Health Institute",
     "provider_type": "dermatologist", "address": "M. M. Alam Road",
     "city": "Lahore", "phone": "+92 42 1234 5604",
     "latitude": 31.5170, "longitude": 74.3520,
     "opening_time": dt_time(9, 30), "closing_time": dt_time(19, 30), "working_days": "Mon-Sat"},
    {"name": "Dr. Mariam Yousaf — Cosmetic Dermatology",
     "provider_type": "dermatologist", "address": "Johar Town C-Block",
     "city": "Lahore", "phone": "+92 42 1234 5605",
     "latitude": 31.4694, "longitude": 74.2735,
     "opening_time": dt_time(10, 0), "closing_time": dt_time(18, 0), "working_days": "Mon-Fri"},

    # ─── Salons (Lahore) ────────────────────────────────────────────
    {"name": "Nabila's Hair & Skin Studio",
     "provider_type": "salon", "address": "Liberty Market, Gulberg",
     "city": "Lahore", "phone": "+92 42 9876 5401",
     "latitude": 31.5125, "longitude": 74.3470,
     "opening_time": dt_time(10, 0), "closing_time": dt_time(21, 0), "working_days": "Mon-Sun"},
    {"name": "Depilex Smileagain — DHA",
     "provider_type": "salon", "address": "Sector Z, DHA Phase 3",
     "city": "Lahore", "phone": "+92 42 9876 5402",
     "latitude": 31.4780, "longitude": 74.4180,
     "opening_time": dt_time(11, 0), "closing_time": dt_time(20, 0), "working_days": "Mon-Sat"},
    {"name": "Allenora Aesthetics",
     "provider_type": "salon", "address": "Phase 5, DHA",
     "city": "Lahore", "phone": "+92 42 9876 5403",
     "latitude": 31.4760, "longitude": 74.4280,
     "opening_time": dt_time(10, 0), "closing_time": dt_time(19, 0), "working_days": "Tue-Sun"},
    {"name": "Madeeha's Signature Salon",
     "provider_type": "salon", "address": "Model Town Link Road",
     "city": "Lahore", "phone": "+92 42 9876 5404",
     "latitude": 31.4845, "longitude": 74.3220,
     "opening_time": dt_time(10, 30), "closing_time": dt_time(20, 30), "working_days": "Mon-Sun"},

    # ─── A few in other cities (so city filter has variety) ────────
    {"name": "Dr. Zeeshan Iqbal — Aesthetic Skin Clinic",
     "provider_type": "dermatologist", "address": "F-7 Markaz",
     "city": "Islamabad", "phone": "+92 51 1234 5611",
     "latitude": 33.7100, "longitude": 73.0560,
     "opening_time": dt_time(9, 30), "closing_time": dt_time(19, 0), "working_days": "Mon-Sat"},
    {"name": "Sara's Beauty Lounge",
     "provider_type": "salon", "address": "Clifton Block 4",
     "city": "Karachi", "phone": "+92 21 9876 5412",
     "latitude": 24.8170, "longitude": 67.0280,
     "opening_time": dt_time(11, 0), "closing_time": dt_time(21, 0), "working_days": "Mon-Sun"},
]


def main():
    created = 0
    skipped = 0
    for data in PROVIDERS:
        obj, was_created = Provider.objects.get_or_create(
            name=data["name"],
            defaults=data,
        )
        if was_created:
            created += 1
            print(f"  ✓ {obj.name}")
        else:
            skipped += 1
    print(f"\nDone. Created {created} new providers. {skipped} already existed.")
    print(f"Total providers now: {Provider.objects.count()}")


if __name__ == "__main__":
    main()
