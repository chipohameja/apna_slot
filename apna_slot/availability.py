from datetime import date

import frappe

from apna_slot.pricing import PriceResolver
from apna_slot.utils.slots import add_minutes, slot_starts, to_time
from apna_slot.utils.timezone import to_utc, today_in, utc_now

AVAILABLE = "available"
BOOKED = "booked"
PAST = "past"
BEYOND_WINDOW = "beyond_window"


class AvailabilityGrid:
	"""Slots for one resource: its schedule, minus the ledger, minus the booking window.
	Closures and the DST filter arrive in Phase 3; the composition order does not change."""

	def __init__(self, resource):
		self.resource = resource if hasattr(resource, "doctype") else frappe.get_doc("Bookable Resource", resource)
		self.venue = frappe.get_cached_doc("Venue", self.resource.venue)
		self.prices = PriceResolver(self.resource)

	def for_date(self, on_date: date) -> list[dict]:
		booked = self._booked_starts(on_date)
		return [self._slot(on_date, start, booked) for start in self._starts_on(on_date)]

	def _starts_on(self, on_date: date) -> list:
		rows = [row for row in self.resource.weekly_schedule if row.day_of_week == on_date.strftime("%A")]
		starts = {start for row in rows for start in slot_starts(row.opens_at, row.closes_at, self._slot_minutes)}
		return sorted(starts)

	def _booked_starts(self, on_date: date) -> set:
		rows = frappe.get_all(
			"Booking Slot",
			filters={"resource": self.resource.name, "slot_date": on_date},
			fields=["start_time"],
		)
		return {to_time(row.start_time) for row in rows}

	def _slot(self, on_date: date, start, booked: set) -> dict:
		price, rule = self.prices.price_for(on_date, start)
		return {
			"start_time": start.isoformat(),
			"end_time": add_minutes(start, self._slot_minutes).isoformat(),
			"status": self._status(on_date, start, booked),
			"price": price,
			"rule": rule,
		}

	def _status(self, on_date: date, start, booked: set) -> str:
		if start in booked:
			return BOOKED
		if self._is_beyond_window(on_date):
			return BEYOND_WINDOW
		return PAST if self._is_too_late(on_date, start) else AVAILABLE

	def _is_beyond_window(self, on_date: date) -> bool:
		return (on_date - today_in(self.venue.timezone)).days > self.venue.max_advance_days

	def _is_too_late(self, on_date: date, start) -> bool:
		"""I-5: a slot closes to new bookings `min_lead_minutes` before it starts."""
		lead = self.venue.min_lead_minutes * 60
		return (to_utc(on_date, start, self.venue.timezone) - utc_now()).total_seconds() < lead

	@property
	def _slot_minutes(self) -> int:
		return int(self.resource.slot_duration_minutes)


def get_day_grid(resource: str, on_date: date) -> list[dict]:
	"""Every slot for one resource on one venue-local date, with status and price."""
	return AvailabilityGrid(resource).for_date(on_date)
