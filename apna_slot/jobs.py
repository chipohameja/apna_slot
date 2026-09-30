import frappe

from apna_slot.booking_engine import release_booking
from apna_slot.utils.timezone import utc_now

EXPIRY_SAVEPOINT = "apna_slot_expiry"


def expire_pending_bookings() -> int:
	"""Every 2 minutes (D-6): a 10-minute hold is back on the grid at most 12 minutes after the
	customer walked away. Returns how many holds it released."""
	return sum(_expire(booking) for booking in _lapsed_holds())


def _lapsed_holds() -> list[str]:
	return frappe.get_all(
		"Booking",
		filters={"status": "Pending Payment", "hold_expires_at": ("<", utc_now())},
		pluck="name",
		order_by="hold_expires_at asc",
	)


def _expire(booking: str) -> bool:
	"""One savepoint per hold, so one bad record cannot stall the queue."""
	frappe.db.savepoint(EXPIRY_SAVEPOINT)
	try:
		release_booking(booking, "Expired")
		return True
	except Exception:
		frappe.db.rollback(save_point=EXPIRY_SAVEPOINT)
		frappe.log_error(title=f"Could not expire booking {booking}", reference_doctype="Booking", reference_name=booking)
		return False
