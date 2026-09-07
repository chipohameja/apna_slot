from datetime import date, time

import frappe
from frappe.utils import add_to_date, getdate

from apna_slot.availability import AVAILABLE, AvailabilityGrid
from apna_slot.constants import HOLD_MINUTES
from apna_slot.exceptions import SlotUnavailableError, refuse_slots
from apna_slot.pricing import PriceResolver
from apna_slot.utils.slots import add_minutes, to_time
from apna_slot.utils.timezone import utc_now

OFF_GRID = "off_grid"
LOCK_ATTEMPTS = 3
CLAIM_SAVEPOINT = "apna_slot_claim"
TRANSIENT_LOCK_ERRORS = (frappe.QueryDeadlockError, frappe.QueryTimeoutError)


class BookingRequest:
	"""One customer's attempt to claim slots on one resource. `submit()` is the critical
	section: the pre-check is courtesy, the unique index is the guarantee (I-1, D-17)."""

	def __init__(self, resource: str, slots: list[tuple[date, time]], customer: str):
		self.resource = frappe.get_doc("Bookable Resource", resource)
		self.slots = slots
		self.customer = customer
		self.prices = PriceResolver(self.resource)

	def submit(self) -> dict:
		self._check_slots_are_free()
		return self.claim()

	def claim(self) -> dict:
		"""The critical section. Frappe's naming counter is a row lock that every insert of a
		doctype contends for, so two customers booking at the same instant can collide there
		before they ever reach the ledger. That is transient — roll back and try again. A slot
		someone else holds is not transient and is never retried."""
		for remaining in reversed(range(LOCK_ATTEMPTS)):
			try:
				return _receipt(self._claim_or_roll_back())
			except TRANSIENT_LOCK_ERRORS:
				frappe.db.rollback()
				if not remaining:
					raise

	def _check_slots_are_free(self):
		"""Courtesy only: it turns 99.9% of collisions into a friendly grid refresh."""
		conflicts = self._conflicting_lines()
		if conflicts:
			refuse_slots(conflicts)

	def _conflicting_lines(self) -> list[dict]:
		grid = AvailabilityGrid(self.resource)
		taken = []
		for slot_date, start_time in self.slots:
			status = _status_of(grid.for_date(slot_date), start_time)
			if status != AVAILABLE:
				taken.append(_conflict(slot_date, start_time, status))
		return taken

	def _claim_or_roll_back(self):
		"""One savepoint over both inserts, so a collision leaves no orphan Booking."""
		frappe.db.savepoint(CLAIM_SAVEPOINT)
		try:
			booking = self._insert_booking()
			self._claim_ledger_rows(booking)
			return booking
		except SlotUnavailableError:
			frappe.db.rollback(save_point=CLAIM_SAVEPOINT)
			raise

	def _insert_booking(self):
		booking = frappe.new_doc("Booking")
		booking.customer = self.customer
		booking.resource = self.resource.name
		booking.status = "Pending Payment"
		booking.hold_expires_at = add_to_date(utc_now(), minutes=HOLD_MINUTES)
		for slot_date, start_time in self.slots:
			booking.append("lines", self._line(slot_date, start_time))
		booking.insert()
		return booking

	def _line(self, slot_date: date, start_time: time) -> dict:
		price, rule = self.prices.price_for(slot_date, start_time)
		return {
			"line_date": slot_date,
			"start_time": start_time,
			"end_time": add_minutes(start_time, int(self.resource.slot_duration_minutes)),
			"price": price,
			"price_rule": rule,
			"status": "Active",
		}

	def _claim_ledger_rows(self, booking):
		for line in booking.lines:
			self._claim(booking, line)

	def _claim(self, booking, line):
		"""Privileged by design: no role writes the ledger, only this function."""
		row = frappe.new_doc("Booking Slot")
		row.update(
			{
				"resource": booking.resource,
				"slot_date": line.line_date,
				"start_time": line.start_time,
				"end_time": line.end_time,
				"booking": booking.name,
				"booking_line": line.name,
			}
		)
		try:
			row.insert(ignore_permissions=True)
		except frappe.UniqueValidationError:
			frappe.clear_last_message()  # "must be unique" is our plumbing, not the customer's problem
			refuse_slots([_conflict(line.line_date, to_time(line.start_time), "booked")])


def create_booking(resource: str, slot_date, start_time, customer: str | None = None) -> dict:
	"""Hold one slot. Phase 3 widens this to many slots across many dates (D-28)."""
	slots = [(getdate(slot_date), to_time(start_time))]
	return BookingRequest(resource, slots, customer or frappe.session.user).submit()


def _status_of(slots: list[dict], start_time: time) -> str:
	wanted = start_time.isoformat()
	return next((slot["status"] for slot in slots if slot["start_time"] == wanted), OFF_GRID)


def _conflict(slot_date: date, start_time: time, reason: str) -> dict:
	return {"date": str(slot_date), "start_time": start_time.isoformat(), "reason": reason}


def _receipt(booking) -> dict:
	return {
		"booking": booking.name,
		"hold_expires_at": str(booking.hold_expires_at),
		"total_amount": booking.total_amount,
		"currency": booking.currency,
		"line_count": booking.line_count,
	}
