import hashlib
import hmac

import frappe
from frappe import _
from frappe.utils.verified_command import get_secret

from apna_slot.gateways.base import OUTCOMES, CallbackResult, PaymentGateway


class MockGateway(PaymentGateway):
	"""Moves no money and skips no steps: it hosts a checkout page, signs its callback and
	refuses a tampered one — so the real gateway inherits a path already under test (D-16)."""

	name = "Mock"

	def create_checkout(self, transaction) -> dict:
		return {
			"redirect_url": f"/apnaslot/pay/{transaction.checkout_token}",
			"gateway_reference": self._reference("MOCK"),
		}

	def verify_callback(self, payload: dict) -> CallbackResult:
		outcome = payload.get("outcome")
		self._check_known_outcome(outcome)
		self._check_signature(payload.get("token"), outcome, payload.get("signature") or "")
		return CallbackResult(outcome, payload.get("gateway_reference"), payload)

	def refund(self, transaction, amount, reason: str) -> dict:
		return {"reference": self._reference("MOCKREF"), "status": "Refunded"}

	def sign(self, token: str, outcome: str) -> str:
		"""The gateway's half of the handshake. Only `api.payment.simulate` may call it, and
		only because it stands in for the gateway's own server."""
		message = f"{token}:{outcome}".encode()
		return hmac.new(get_secret().encode(), message, hashlib.sha256).hexdigest()

	def _check_known_outcome(self, outcome) -> None:
		if outcome not in OUTCOMES:
			frappe.throw(_("{0} is not a payment outcome").format(outcome))

	def _check_signature(self, token, outcome: str, signature: str) -> None:
		if not token or not hmac.compare_digest(self.sign(token, outcome), signature):
			frappe.throw(_("This payment result could not be verified"), frappe.PermissionError)

	def _reference(self, prefix: str) -> str:
		return f"{prefix}-{frappe.generate_hash(length=10).upper()}"
