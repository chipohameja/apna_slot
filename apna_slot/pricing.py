from datetime import date, time
from decimal import Decimal

from frappe.utils import flt

BASE_PRICE_LABEL = "Base Price"


class PriceResolver:
	"""Prices every slot of one resource. Constructed once per resource so Phase 2 can
	match rules without re-reading the document per slot (D-12)."""

	def __init__(self, resource):
		self.resource = resource

	def price_for(self, slot_date: date, slot_start: time) -> tuple[Decimal, str]:
		return flt(self.resource.base_price), BASE_PRICE_LABEL


def resolve_slot_price(resource, slot_date: date, slot_start: time) -> tuple[Decimal, str]:
	"""Return (price, rule_label) for one slot."""
	return PriceResolver(resource).price_for(slot_date, slot_start)
