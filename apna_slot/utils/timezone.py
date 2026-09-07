from functools import lru_cache
from zoneinfo import ZoneInfo, available_timezones

import frappe
from frappe import _


@lru_cache(maxsize=1)
def known_timezones() -> frozenset[str]:
	return frozenset(available_timezones())


def validate_timezone(name: str) -> None:
	"""Throw unless `name` is an IANA identifier the runtime knows."""
	if name not in known_timezones():
		frappe.throw(_("{0} is not a valid timezone identifier").format(name))


def zone(name: str) -> ZoneInfo:
	return ZoneInfo(name)
