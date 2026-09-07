import frappe

no_cache = 1


def get_context(context):
	context.boot = get_boot()
	return context


def get_boot():
	"""Injected into the SPA as window[key] by frappe-ui's jinjaBootData plugin."""
	return {
		"csrf_token": frappe.sessions.get_csrf_token(),
		"site_name": frappe.local.site,
	}
