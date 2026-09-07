from datetime import UTC, date, datetime, time
from functools import lru_cache
from zoneinfo import ZoneInfo, available_timezones

import frappe
from frappe import _

from apna_slot.utils.slots import to_time


@lru_cache(maxsize=1)
def known_timezones() -> frozenset[str]:
	return frozenset(available_timezones())


def validate_timezone(name: str) -> None:
	"""Throw unless `name` is an IANA identifier the runtime knows."""
	if name not in known_timezones():
		frappe.throw(_("{0} is not a valid timezone identifier").format(name))


def zone(name: str) -> ZoneInfo:
	return ZoneInfo(name)


def utc_now() -> datetime:
	"""Naive UTC. The system's one time axis (D-9) — `frappe.utils.now_datetime` is site-local."""
	return datetime.now(UTC).replace(tzinfo=None)


def to_utc(local_date: date, local_time, timezone: str) -> datetime:
	"""A venue-local wall clock as a naive UTC instant (D-9)."""
	local = datetime.combine(local_date, to_time(local_time), tzinfo=zone(timezone))
	return local.astimezone(UTC).replace(tzinfo=None)


def today_in(timezone: str) -> date:
	"""The venue's own calendar date, which is what a booking window is measured in."""
	return datetime.now(zone(timezone)).date()
