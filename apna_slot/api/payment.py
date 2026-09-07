import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from apna_slot.exceptions import refuse_expired_hold
from apna_slot.gateways import get_gateway
from apna_slot.gateways.mock import MockGateway
from apna_slot.utils.timezone import utc_now

HELD = "Pending Payment"
LIVE_STATUSES = ("Created", "Pending")


@frappe.whitelist(methods=["POST"])
def start(booking: str) -> dict:
	"""Open a hosted checkout for a hold the caller still owns."""
	document = _own_booking(booking)
	_check_hold_stands(document)
	return _transaction_for(document).open_checkout()


@frappe.whitelist(methods=["GET"])
def get_checkout(token: str) -> dict:
	"""The summary the hosted gateway page renders. Owner only."""
	return _own_transaction(token).checkout_summary()


@frappe.whitelist(methods=["POST"])
def simulate(token: str, outcome: str) -> dict:
	"""Mock only. Plays the gateway's own server — it signs the outcome and posts it to
	`callback`, so what a button press exercises is the production path, not a shortcut."""
	gateway = _mock_gateway()
	_own_transaction(token)
	return callback(token, outcome, gateway.sign(token, outcome))


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="token", limit=20, seconds=60)
def callback(token: str, outcome: str, signature: str) -> dict:
	"""The gateway's webhook. The signature decides whether we listen, and the gateway's
	verdict — never the caller's claim — decides what happens to the booking."""
	payload = {"token": token, "outcome": outcome, "signature": signature}
	result = get_gateway().verify_callback(payload)
	return _transaction(token).apply(result)


def _own_booking(booking: str):
	"""Only the customer pays for their own hold; a publisher reading it is not paying it."""
	document = frappe.get_doc("Booking", booking)
	if document.customer != frappe.session.user:
		frappe.throw(_("No such booking"), frappe.DoesNotExistError)
	return document


def _check_hold_stands(booking) -> None:
	if booking.status != HELD:
		frappe.throw(_("This booking is {0} and can no longer be paid for").format(booking.status))
	if booking.hold_expires_at and booking.hold_expires_at < utc_now():
		refuse_expired_hold(booking.hold_expires_at)


def _transaction_for(booking):
	"""One live transaction per hold: a second checkout would strand the first."""
	live = frappe.db.get_value(
		"Payment Transaction", {"booking": booking.name, "status": ("in", LIVE_STATUSES)}
	)
	return frappe.get_doc("Payment Transaction", live) if live else _new_transaction(booking)


def _new_transaction(booking):
	"""The customer never writes the payment ledger; this function does it on their behalf."""
	transaction = frappe.new_doc("Payment Transaction")
	transaction.update(
		{
			"booking": booking.name,
			"gateway": get_gateway().name,
			"amount": booking.total_amount,
			"currency": booking.currency,
			"expires_at": booking.hold_expires_at,
		}
	)
	transaction.insert(ignore_permissions=True)
	return transaction


def _transaction(token: str):
	"""Found by bearer token and nothing else. An unknown token is a 404, never a 403."""
	name = frappe.db.get_value("Payment Transaction", {"checkout_token": token})
	if not name:
		frappe.throw(_("No such payment"), frappe.DoesNotExistError)
	return frappe.get_doc("Payment Transaction", name)


def _own_transaction(token: str):
	transaction = _transaction(token)
	if frappe.db.get_value("Booking", transaction.booking, "customer") != frappe.session.user:
		frappe.throw(_("No such payment"), frappe.DoesNotExistError)
	return transaction


def _mock_gateway() -> MockGateway:
	gateway = get_gateway()
	if gateway.name != MockGateway.name:
		frappe.throw(_("Simulated payments exist only on the mock gateway"))
	return gateway
