import frappe
from frappe import _
from frappe.utils import getdate

from apna_slot.availability import get_day_grid


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_day(resource: str, date: str) -> list[dict]:
	"""Every slot for one resource on one venue-local date."""
	check_resource_is_public(resource)
	return get_day_grid(resource, getdate(date))


def check_resource_is_public(resource: str) -> None:
	"""Opening hours are venue data: only a published venue exposes them (D-34).
	Unpublished reads as 404, never 403 — a 403 confirms the venue exists."""
	venue = frappe.db.get_value("Bookable Resource", resource, "venue")
	if not venue or frappe.db.get_value("Venue", venue, "status") != "Published":
		frappe.throw(_("No such resource"), frappe.DoesNotExistError)
