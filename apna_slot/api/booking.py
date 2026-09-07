import frappe

from apna_slot.api.availability import check_resource_is_public
from apna_slot.booking_engine import create_booking


@frappe.whitelist(methods=["POST"])
def create(resource: str, slot_date: str, start_time: str) -> dict:
	"""Hold one slot for the logged-in customer. 409 with `conflicting_lines` on collision."""
	check_resource_is_public(resource)
	return create_booking(resource, slot_date, start_time)
