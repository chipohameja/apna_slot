import frappe
from frappe import _

from apna_slot.gateways.base import PaymentGateway
from apna_slot.gateways.mock import MockGateway

SITE_CONFIG_KEY = "apna_slot_payment_gateway"
GATEWAYS = {gateway.name: gateway for gateway in (MockGateway,)}


def get_gateway(name: str | None = None) -> PaymentGateway:
	"""The site's payment gateway. A real one is a new entry here, not a new flow (D-16)."""
	name = name or frappe.conf.get(SITE_CONFIG_KEY) or MockGateway.name
	if name not in GATEWAYS:
		frappe.throw(_("No payment gateway named {0}").format(name))
	return GATEWAYS[name]()
