app_name = "apna_slot"
app_title = "Apna Slot"
app_publisher = "Chipo"
app_description = "Multi-tenant venue slot booking"
app_email = "chipo@mail.com"
app_license = "agpl-3.0"

# The SPA. /apnaslot/* is public and customer-facing, /apnaslot/manage/* is the
# publisher dashboard; both are served by the same Vue app (D-3).
website_route_rules = [
	{"from_route": "/apnaslot/<path:app_path>", "to_route": "apnaslot"},
]

# --- Tenant isolation (extended by every later phase) ------------------
permission_query_conditions = {
	"Publisher": "apna_slot.permissions.publisher_query",
	"Venue": "apna_slot.permissions.tenant_query",
	"Bookable Resource": "apna_slot.permissions.tenant_query",
	"Booking Slot": "apna_slot.permissions.tenant_query",
	"Booking": "apna_slot.permissions.booking_query",
	"Payment Transaction": "apna_slot.permissions.tenant_query",
}
has_permission = {
	"Publisher": "apna_slot.permissions.publisher_has_permission",
	"Venue": "apna_slot.permissions.tenant_has_permission",
	"Bookable Resource": "apna_slot.permissions.tenant_has_permission",
	"Booking Slot": "apna_slot.permissions.tenant_has_permission",
	"Booking": "apna_slot.permissions.booking_has_permission",
	"Payment Transaction": "apna_slot.permissions.tenant_has_permission",
}

# --- Fixtures ----------------------------------------------------------
fixtures = [
	{"dt": "Role", "filters": [["role_name", "in", ["Apna Slot Customer", "Apna Slot Publisher"]]]},
]

# --- Scheduler ---------------------------------------------------------
scheduler_events = {
	"cron": {
		"*/2 * * * *": ["apna_slot.jobs.expire_pending_bookings"],
	},
}
