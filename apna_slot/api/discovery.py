import frappe
from frappe.query_builder import Order
from frappe.query_builder.functions import Count, Min

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
