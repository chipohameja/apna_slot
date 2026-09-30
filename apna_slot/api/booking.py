import frappe

from apna_slot.api.availability import check_resource_is_public
from apna_slot.booking_engine import create_booking

BOOKING_FIELDS = [
	"name",
	"status",
	"venue.venue_name as venue_name",
	"resource.resource_name as resource_name",
	"first_start_utc",
	"total_amount",
	"currency",
]


@frappe.whitelist(methods=["POST"])
def create(resource: str, slot_date: str, start_time: str) -> dict:
	"""Hold one slot for the logged-in customer. 409 with `conflicting_lines` on collision."""
	check_resource_is_public(resource)
	return create_booking(resource, slot_date, start_time)


@frappe.whitelist(methods=["GET"])
def list_mine() -> list[dict]:
	"""The caller's own bookings, latest slot first. Released holds have no instant and sink last.
	A publisher member reading this sees their purchases, never their venue's sales."""
	bookings = frappe.get_all(
		"Booking",
		filters={"customer": frappe.session.user},
		fields=BOOKING_FIELDS,
		order_by="first_start_utc desc, creation desc",
	)
	first_lines = _first_lines([booking.name for booking in bookings])
	for booking in bookings:
		booking.update(first_lines.get(booking.name, {}))
	return bookings


def _first_lines(bookings: list[str]) -> dict[str, dict]:
	"""Each booking's earliest line, the one a list row names. A series is one row, not six."""
	lines = frappe.get_all(
		"Booking Line",
		filters={"parent": ("in", bookings or [""]), "parenttype": "Booking"},
		fields=["parent", "line_date", "start_time", "end_time"],
		order_by="line_date asc, start_time asc",
	)
	first = {}
	for line in lines:
		first.setdefault(line.pop("parent"), line)
	return first
