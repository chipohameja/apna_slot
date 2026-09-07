import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.query_builder.functions import Count, Min

VENUE_FIELDS = ["name", "venue_name", "slug", "city", "country", "timezone", "currency", "max_advance_days", "min_lead_minutes"]
RESOURCE_FIELDS = ["name", "resource_name", "slot_duration_minutes", "base_price"]

# The public read path (D-34): tenant permission queries never widen to published
# rows, so every function here states `status = "Published"` for itself.


@frappe.whitelist(allow_guest=True, methods=["GET"])
def search_venues() -> list[dict]:
	"""Published venues that have at least one active resource. Filters arrive in Phase 5."""
	venue = frappe.qb.DocType("Venue")
	resource = frappe.qb.DocType("Bookable Resource")
	return (
		frappe.qb.from_(venue)
		.inner_join(resource)
		.on(resource.venue == venue.name)
		.select(
			venue.slug,
			venue.venue_name,
			venue.city,
			venue.country,
			venue.currency,
			Min(resource.base_price).as_("from_price"),
			Count(resource.name).as_("resource_count"),
		)
		.where((venue.status == "Published") & (resource.status == "Active"))
		.groupby(venue.name)
		.orderby(venue.creation, order=Order.desc)
		.run(as_dict=True)
	)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_venue(slug: str) -> dict:
	"""One published venue with its active resources. Draft or unlisted reads as 404."""
	venue = _published_venue(slug)
	venue["resources"] = _active_resources(venue["name"])
	return venue


def _published_venue(slug: str) -> dict:
	rows = frappe.get_all(
		"Venue", filters={"slug": slug, "status": "Published"}, fields=VENUE_FIELDS, limit=1
	)
	if not rows:
		frappe.throw(_("No such venue"), frappe.DoesNotExistError)
	return rows[0]


def _active_resources(venue: str) -> list[dict]:
	return frappe.get_all(
		"Bookable Resource",
		filters={"venue": venue, "status": "Active"},
		fields=RESOURCE_FIELDS,
		order_by="creation asc",
	)
