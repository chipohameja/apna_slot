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
