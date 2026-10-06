"""Seed script for E2E Playwright tests.

Run via: bench --site <site> execute apna_slot.e2e_seed.setup_e2e_data
"""

import frappe
from frappe.utils.password import update_password

from apna_slot.api.publisher import create_publisher
from apna_slot.tests.fixtures import make_customer, make_resource, make_venue

PUBLISHER_NAME = "E2E Sports"
VENUE_NAME = "E2E Sports Arena"
CUSTOMER_EMAIL = "customer@example.com"
CUSTOMER_PASSWORD = "admin"


def setup_e2e_data():
	"""Administrator's publisher with one published venue, and a customer to book it."""
	_ensure_customer()
	frappe.set_user("Administrator")
	publisher = _ensure_publisher()
	_ensure_published_venue(publisher)
	frappe.db.commit()


def _ensure_customer() -> None:
	if not frappe.db.exists("User", CUSTOMER_EMAIL):
		make_customer(CUSTOMER_EMAIL, "Raj Customer")
	update_password(CUSTOMER_EMAIL, CUSTOMER_PASSWORD)


def _ensure_publisher() -> str:
	existing = frappe.db.get_value("Publisher", {"publisher_name": PUBLISHER_NAME}, "name")
	if existing:
		return existing
	created = create_publisher(
		publisher_name=PUBLISHER_NAME,
		contact_email="admin@example.com",
		currency="AED",
		timezone="Asia/Dubai",
	)
	return created["name"]


def _ensure_published_venue(publisher: str) -> None:
	if frappe.db.exists("Venue", {"venue_name": VENUE_NAME, "publisher": publisher}):
		return
	venue = make_venue(publisher, VENUE_NAME)
	make_resource(venue)
	published = frappe.get_doc("Venue", venue)
	published.status = "Published"
	published.save()
