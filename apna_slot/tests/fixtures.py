import threading
from dataclasses import dataclass

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


@dataclass
class Arena:
	"""A committed publisher/venue/resource, for tests that need a second connection to see it."""

	publisher: str
	venue: str
	resource: str
	users: list[str]


def in_own_connection(work):
	"""Run `work` on its own connection. Committing on the test's connection would commit
	every row the tests before it created, which then outlive the suite."""
	site = frappe.local.site
	outcome = {}

	def run():
		frappe.init(site=site)
		frappe.connect()
		try:
			outcome["value"] = work()
			frappe.db.commit()
		except Exception as failure:
			frappe.db.rollback()
			outcome["error"] = failure
		finally:
			frappe.destroy()

	thread = threading.Thread(target=run)
	thread.start()
	thread.join(timeout=120)
	if "error" in outcome:
		raise outcome["error"]
	return outcome.get("value")


def make_committed_arena(prefix: str, customers: int = 2) -> Arena:
	"""A publisher, venue and resource visible to other connections — what a race needs.
	Salted, because these rows are committed: a run whose teardown fails must not poison
	the next one with a half-built arena of the same name."""
	salted = f"{prefix}-{frappe.generate_hash(length=6)}"
	return in_own_connection(lambda: _build_arena(salted, customers))


def drop_committed_arena(arena: Arena) -> None:
	in_own_connection(lambda: _drop_arena(arena))


def _build_arena(prefix: str, customers: int) -> Arena:
	owner = make_customer(f"{prefix}.owner@example.com", "Ola Owner")
	publisher = make_publisher(owner, f"Tracer {prefix} Publisher")
	venue = make_venue(publisher, f"Tracer {prefix} Arena")
	resource = make_resource(venue)
	users = [owner] + [make_customer(f"{prefix}.customer{index}@example.com") for index in range(customers)]
	frappe.set_user("Administrator")
	return Arena(publisher=publisher, venue=venue, resource=resource, users=users)


def _drop_arena(arena: Arena) -> None:
	frappe.set_user("Administrator")
	bookings = frappe.get_all("Booking", filters={"resource": arena.resource}, pluck="name")
	frappe.db.delete("Booking Slot", {"resource": arena.resource})
	frappe.db.delete("Booking Line", {"parent": ("in", bookings or [""])})
	frappe.db.delete("Booking", {"resource": arena.resource})
	for doctype, name in (
		("Bookable Resource", arena.resource),
		("Venue", arena.venue),
		("Publisher", arena.publisher),
	):
		frappe.delete_doc(doctype, name, force=True, ignore_permissions=True, delete_permanently=True)
	for user in arena.users:
		frappe.delete_doc("User", user, force=True, ignore_permissions=True, delete_permanently=True)
