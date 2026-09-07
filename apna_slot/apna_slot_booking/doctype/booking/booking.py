import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from apna_slot.utils.timezone import to_utc

HOLDING_STATUSES = {"Pending Payment", "Confirmed", "Completed"}


class Booking(Document):
	def before_insert(self):
		self._snapshot_venue()
		self._stamp_line_instants()

	def validate(self):
		self._check_has_lines()
		self._recompute_rollups()

	def on_trash(self):
		frappe.throw(_("Bookings are cancelled, never deleted"))

	def confirm(self) -> None:
		"""Payment landed: the hold ends and every ledger row stays where it is (I-2)."""
		self.status = "Confirmed"
		self.hold_expires_at = None
		self.save(ignore_permissions=True)

	def release(self, status: str) -> None:
		"""The slots have gone back to the grid, so the lines that held them are cancelled.
		Privileged: the callback that calls this may be running as the gateway, not as a user."""
		for line in self.active_lines:
			line.status = "Cancelled"
		self.status = status
		self.hold_expires_at = None
		self.save(ignore_permissions=True)

	@property
	def active_lines(self) -> list:
		return [line for line in self.lines if line.status == "Active"]

	def _snapshot_venue(self):
		"""Taken once. A later venue edit must not move a booking that already exists (I-9)."""
		venue = frappe.get_cached_doc("Venue", self.venue)
		self.timezone = venue.timezone
		self.currency = venue.currency

	def _stamp_line_instants(self):
		for line in self.lines:
			line.start_utc = to_utc(line.line_date, line.start_time, self.timezone)
			line.end_utc = to_utc(line.line_date, line.end_time, self.timezone)

	def _check_has_lines(self):
		if not self.lines:
			frappe.throw(_("A booking needs at least one slot"))

	def _recompute_rollups(self):
		"""Derived from the lines every time — never set by a caller."""
		active = self.active_lines
		self.line_count = len(self.lines)
		self.active_line_count = len(active)
		self.total_amount = sum(flt(line.price) for line in self.lines)
		self.first_start_utc = min((line.start_utc for line in active), default=None)
		self.last_end_utc = max((line.end_utc for line in active), default=None)
