import itertools
from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate

from apna_slot import jobs
from apna_slot.api.booking import list_mine
from apna_slot.availability import get_day_grid
from apna_slot.booking_engine import confirm_booking, create_booking, release_booking
from apna_slot.permissions import clear_publisher_cache
from apna_slot.tests.fixtures import drop_committed_arena, make_committed_arena
from apna_slot.utils.timezone import utc_now


class TestExpiry(IntegrationTestCase):
	"""R6. Shares one committed arena for the reason `TestPayment` does: user creation is
	throttled, and a hold is all these tests need."""

	_unused_days = itertools.count(40)

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.arena = make_committed_arena("expiry", customers=2)
		cls.customer, cls.stranger = cls.arena.users[1], cls.arena.users[2]

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		drop_committed_arena(cls.arena)
		super().tearDownClass()

	def setUp(self):
		super().setUp()
		clear_publisher_cache()
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_expiry_job_releases_hold(self):
		"""**R6.** An abandoned hold is back on the grid after one sweep (I-2)."""
		booking, day = self._hold()
		self._lapse(booking)

		jobs.expire_pending_bookings()

		document = frappe.get_doc("Booking", booking)
		self.assertEqual((document.status, document.active_line_count), ("Expired", 0))
		self.assertIsNone(document.hold_expires_at)
		self.assertEqual(frappe.db.count("Booking Slot", {"booking": booking}), 0)
		self.assertEqual(self._status_at_seven(day), "available")

	def test_expiry_job_leaves_a_live_hold_alone(self):
		booking, _ = self._hold()

		jobs.expire_pending_bookings()

		self.assertEqual(frappe.db.get_value("Booking", booking, "status"), "Pending Payment")
		self.assertEqual(frappe.db.count("Booking Slot", {"booking": booking}), 1)

	def test_expiry_job_ignores_confirmed(self):
		"""A paid booking has no hold to lapse, and its ledger row must stay (I-2)."""
		booking, _ = self._hold()
		confirm_booking(booking)

		jobs.expire_pending_bookings()

		self.assertEqual(frappe.db.get_value("Booking", booking, "status"), "Confirmed")
		self.assertEqual(frappe.db.count("Booking Slot", {"booking": booking}), 1)

	def test_expiry_job_survives_a_bad_record(self):
		"""One booking that cannot be released must not stall the queue behind it."""
		broken, _ = self._hold()
		healthy, _ = self._hold()
		self._lapse(broken, minutes=2)
		self._lapse(healthy, minutes=1)

		with patch.object(jobs, "release_booking", side_effect=self._fail_for(broken)):
			jobs.expire_pending_bookings()

		self.assertEqual(frappe.db.get_value("Booking", broken, "status"), "Pending Payment")
		self.assertEqual(frappe.db.get_value("Booking", healthy, "status"), "Expired")
		self.assertTrue(frappe.db.exists("Error Log", {"reference_name": broken}))

	def test_list_mine_shows_only_the_callers_bookings(self):
		mine, day = self._hold()
		self._hold(customer=self.stranger)

		frappe.set_user(self.customer)
		listed = {booking.name: booking for booking in list_mine()}

		self.assertIn(mine, listed)
		self.assertTrue(all(frappe.db.get_value("Booking", name, "customer") == self.customer for name in listed))
		self.assertEqual(listed[mine].line_date, day)
		self.assertEqual(listed[mine].resource_name, "Turf A")

	def _hold(self, customer: str | None = None) -> tuple[str, object]:
		"""A live hold on a date of its own; tests in one class see each other's rows."""
		day = getdate(add_days(getdate(), next(self._unused_days)))
		receipt = create_booking(self.arena.resource, day, "19:00:00", customer=customer or self.customer)
		return receipt["booking"], day

	def _lapse(self, booking: str, minutes: int = 1) -> None:
		"""Time is moved, never waited for (03-testing.md §2.4)."""
		frappe.db.set_value("Booking", booking, "hold_expires_at", utc_now() - timedelta(minutes=minutes))

	def _status_at_seven(self, day) -> str:
		grid = get_day_grid(self.arena.resource, day)
		return next(slot["status"] for slot in grid if slot["start_time"] == "19:00:00")

	@staticmethod
	def _fail_for(broken: str):
		def release(booking, status):
			if booking == broken:
				raise frappe.ValidationError("simulated corruption")
			return release_booking(booking, status)

		return release
