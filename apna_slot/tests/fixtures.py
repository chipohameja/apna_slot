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


def make_venue(publisher: str, venue_name: str, timezone: str = "Asia/Dubai", **overrides) -> str:
	"""A draft venue owned by `publisher`, created as whoever is logged in."""
	venue = frappe.get_doc(
		{
			"doctype": "Venue",
			"publisher": publisher,
			"venue_name": venue_name,
			"address_line_1": "1 Tracer Road",
			"city": "Dubai",
			"country": "United Arab Emirates",
			"timezone": timezone,
			**overrides,
		}
	)
	venue.insert()
	return venue.name


def make_resource(venue: str, resource_name: str = "Turf A", **overrides) -> str:
	"""A resource open 18:00-22:00 every day at 60-minute slots — the tracer's one resource."""
	resource = frappe.get_doc(
		{
			"doctype": "Bookable Resource",
			"venue": venue,
			"resource_name": resource_name,
			"slot_duration_minutes": "60",
			"base_price": 250,
			"weekly_schedule": every_day("18:00:00", "22:00:00"),
			**overrides,
		}
	)
	resource.insert()
	return resource.name


def every_day(opens_at: str, closes_at: str) -> list[dict]:
	return [
		{"day_of_week": day, "opens_at": opens_at, "closes_at": closes_at}
		for day in (
			"Monday",
			"Tuesday",
			"Wednesday",
			"Thursday",
			"Friday",
			"Saturday",
			"Sunday",
		)
	]
