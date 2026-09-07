import frappe

from apna_slot.api.auth import sign_up
from apna_slot.api.publisher import create_publisher

PASSWORD = "Tracer-Bullet-9271"


def make_customer(email: str, full_name: str = "Test Customer") -> str:
	"""Sign a customer up through the real API and leave them logged in."""
	frappe.set_user("Guest")
	sign_up(email=email, full_name=full_name, password=PASSWORD)
	return email


def make_publisher(
	owner: str,
	publisher_name: str,
	timezone: str = "Asia/Dubai",
	currency: str = "AED",
) -> str:
	"""Create a business owned by `owner` through the real API."""
	frappe.set_user(owner)
	created = create_publisher(
		publisher_name=publisher_name,
		contact_email=owner,
		currency=currency,
		timezone=timezone,
	)
	return created["name"]
