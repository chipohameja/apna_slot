import json

import frappe
from frappe.model.document import Document

from apna_slot.booking_engine import confirm_booking, release_booking
from apna_slot.gateways import get_gateway
from apna_slot.gateways.base import ABANDONED, FAILED, SUCCEEDED, CallbackResult

HELD = "Pending Payment"
SETTLED_STATUSES = {"Succeeded", "Failed", "Refunded"}
OUTCOME_STATUSES = {SUCCEEDED: "Succeeded", FAILED: "Failed", ABANDONED: "Abandoned"}


class PaymentTransaction(Document):
	def before_insert(self):
		self.checkout_token = frappe.generate_hash(length=32)

	def open_checkout(self) -> dict:
		"""Ask the gateway for a hosted page and hand the SPA the redirect it answers with."""
		checkout = get_gateway(self.gateway).create_checkout(self)
		self.db_set({"gateway_reference": checkout["gateway_reference"], "status": "Pending"})
		return {
			"redirect_url": checkout["redirect_url"],
			"checkout_token": self.checkout_token,
			"expires_at": str(self.expires_at),
		}

	def apply(self, result: CallbackResult) -> dict:
		"""Record the gateway's verdict and move the booking with it. Idempotent: a repeated
		callback for a settled transaction confirms nothing a second time."""
		if self.status in SETTLED_STATUSES:
			return self.outcome()
		self._record(result)
		self._drive_booking(result.outcome)
		return self.outcome()

	def outcome(self) -> dict:
		return {
			"transaction": self.name,
			"status": self.status,
			"booking": self.booking,
			"booking_status": self._booking_status(),
		}

	def checkout_summary(self) -> dict:
		"""What the hosted gateway page shows the customer before they decide."""
		booking = frappe.get_doc("Booking", self.booking)
		return {
			"booking": booking.name,
			"venue_name": frappe.db.get_value("Venue", booking.venue, "venue_name"),
			"resource_name": frappe.db.get_value("Bookable Resource", booking.resource, "resource_name"),
			"lines": _summary_lines(booking),
			"amount": self.amount,
			"currency": self.currency,
			"expires_at": str(self.expires_at),
			"status": self.status,
		}

	def _record(self, result: CallbackResult) -> None:
		self.db_set(
			{
				"status": OUTCOME_STATUSES[result.outcome],
				"gateway_reference": result.gateway_reference or self.gateway_reference,
				"callback_payload": json.dumps(result.raw, default=str),
			}
		)

	def _drive_booking(self, outcome: str) -> None:
		"""Abandonment moves nothing on purpose: only the timer may release a hold the
		customer walked away from (D-16)."""
		if outcome == SUCCEEDED and self._hold_still_stands():
			confirm_booking(self.booking)
		elif outcome == FAILED:
			release_booking(self.booking, "Payment Failed")

	def _hold_still_stands(self) -> bool:
		"""Expiry beats success: a lapsed hold may already belong to someone else, so a late
		`succeeded` never resurrects it. Phase 4 raises the Refund that owes the customer."""
		return self._booking_status() == HELD

	def _booking_status(self) -> str:
		return frappe.db.get_value("Booking", self.booking, "status")


def _summary_lines(booking) -> list[dict]:
	return [
		{"line_date": str(line.line_date), "start_time": str(line.start_time), "end_time": str(line.end_time)}
		for line in booking.lines
	]
