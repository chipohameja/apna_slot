import itertools
import threading

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate

from apna_slot.api import payment
from apna_slot.api.auth import CUSTOMER_ROLE, get_session_user
from apna_slot.api.discovery import search_venues
from apna_slot.availability import get_day_grid
from apna_slot.booking_engine import BookingRequest, create_booking, release_booking
from apna_slot.constants import HOLD_MINUTES
from apna_slot.exceptions import SlotUnavailableError
from apna_slot.gateways.base import ABANDONED, FAILED, SUCCEEDED
from apna_slot.patches.v1_0.add_booking_slot_unique_index import INDEX_NAME
from apna_slot.apna_slot_core.doctype.publisher.publisher import PUBLISHER_ROLE
from apna_slot.permissions import clear_publisher_cache, publisher_query
from apna_slot.tests.fixtures import (
	drop_committed_arena,
	every_day,
	make_committed_arena,
	make_customer,
	make_publisher,
	make_resource,
	make_venue,
)
from apna_slot.utils.roles import grant_role
from apna_slot.utils.slots import to_time
from apna_slot.utils.timezone import utc_now


class TestTracer(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		clear_publisher_cache()
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_signup_creates_customer_role(self):
		email = make_customer("asha.tracer@example.com", "Asha Bhat")

		user = frappe.get_doc("User", email)
		self.assertEqual(user.user_type, "Website User")
		self.assertIn(CUSTOMER_ROLE, {row.role for row in user.roles})

	def test_signup_logs_the_new_customer_in(self):
		email = make_customer("bootstrap.tracer@example.com", "Boot Strap")

		session = get_session_user()
		self.assertEqual(session["user"], email)
		self.assertFalse(session["is_guest"])
		self.assertEqual(session["publishers"], [])

	def test_create_publisher_grants_publisher_role(self):
		owner = make_customer("owner.tracer@example.com", "Ola Owner")
		publisher = make_publisher(owner, "Tracer Sports Arena")

		self.assertIn(PUBLISHER_ROLE, frappe.get_roles(owner))
		self.assertEqual(get_session_user()["publishers"][0]["name"], publisher)

	def test_taken_business_name_is_refused_by_name(self):
		make_publisher(make_customer("taken.tracer@example.com", "Fay First"), "Tracer Taken Name")
		second = make_customer("latecomer.tracer@example.com", "Sid Second")

		with self.assertRaisesRegex(frappe.ValidationError, "Tracer Taken Name is already listed"):
			make_publisher(second, "Tracer Taken Name")

	def test_query_conditions_scope_to_membership(self):
		"""I-8: a member's list is exactly their own tenant."""
		owner_a = make_customer("a.tracer@example.com", "Ann A")
		publisher_a = make_publisher(owner_a, "Tracer Publisher A")
		owner_b = make_customer("b.tracer@example.com", "Ben B")
		make_publisher(owner_b, "Tracer Publisher B")

		frappe.set_user(owner_a)
		self.assertEqual([row.name for row in frappe.get_list("Publisher")], [publisher_a])

	def test_query_conditions_fail_closed_for_non_member(self):
		"""I-8: the publisher role without a membership matches no rows, not every row."""
		owner = make_customer("held.tracer@example.com", "Hana Held")
		make_publisher(owner, "Tracer Publisher C")
		outsider = make_customer("outsider.tracer@example.com", "Otto Out")
		grant_role(outsider, PUBLISHER_ROLE)

		frappe.set_user(outsider)
		self.assertEqual(publisher_query(outsider), "1=0")
		self.assertEqual(frappe.get_list("Publisher"), [])

	def test_venue_takes_a_slug_from_its_name(self):
		owner = make_customer("slug.tracer@example.com", "Sam Slug")
		publisher = make_publisher(owner, "Tracer Slug Publisher")
		venue_name = unused_venue_name()

		venue = make_venue(publisher, venue_name)

		expected = frappe.scrub(venue_name).replace("_", "-")
		self.assertEqual(frappe.db.get_value("Venue", venue, "slug"), expected)

	def test_second_venue_of_the_same_name_gets_a_distinct_slug(self):
		owner = make_customer("dupe.tracer@example.com", "Dee Dupe")
		publisher = make_publisher(owner, "Tracer Dupe Publisher")
		venue_name = unused_venue_name()

		first = make_venue(publisher, venue_name)
		second = make_venue(publisher, venue_name)

		base = frappe.db.get_value("Venue", first, "slug")
		self.assertEqual(frappe.db.get_value("Venue", second, "slug"), f"{base}-2")

	def test_venue_inherits_locale_from_its_publisher(self):
		owner = make_customer("locale.tracer@example.com", "Lena Locale")
		publisher = make_publisher(owner, "Tracer Locale Publisher", timezone="Asia/Kolkata", currency="INR")

		venue = frappe.get_doc("Venue", make_venue(publisher, "Kolkata Courts", timezone=None))

		self.assertEqual((venue.timezone, venue.currency), ("Asia/Kolkata", "INR"))

	def test_resource_denormalises_publisher_from_its_venue(self):
		owner = make_customer("denorm.tracer@example.com", "Dan Denorm")
		publisher = make_publisher(owner, "Tracer Denorm Publisher")
		venue = make_venue(publisher, "Denorm Arena")

		resource = frappe.get_doc("Bookable Resource", make_resource(venue))

		self.assertEqual(resource.publisher, publisher)
		self.assertEqual(resource.currency, "AED")

	def test_venue_query_scopes_to_membership(self):
		"""I-8: the tenant boundary covers inventory, not just the Publisher record."""
		owner_a = make_customer("va.tracer@example.com", "Vic A")
		venue_a = make_venue(make_publisher(owner_a, "Tracer Venue Publisher A"), "Arena A")
		owner_b = make_customer("vb.tracer@example.com", "Vic B")
		make_venue(make_publisher(owner_b, "Tracer Venue Publisher B"), "Arena B")

		frappe.set_user(owner_a)
		self.assertEqual([row.name for row in frappe.get_list("Venue")], [venue_a])

	def test_venue_of_another_publisher_is_not_readable(self):
		"""I-8: the row-level hook refuses the document, not just the list."""
		owner_a = make_customer("ra.tracer@example.com", "Rita A")
		venue_a = make_venue(make_publisher(owner_a, "Tracer Read Publisher A"), "Read Arena A")
		owner_b = make_customer("rb.tracer@example.com", "Rob B")
		make_publisher(owner_b, "Tracer Read Publisher B")

		frappe.set_user(owner_b)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc("Venue", venue_a).check_permission("read")

	def test_resource_on_another_publishers_venue_is_refused(self):
		"""The publisher is fetched after the create check, so it resolves through the venue."""
		owner_a = make_customer("xa.tracer@example.com", "Xena A")
		venue_a = make_venue(make_publisher(owner_a, "Tracer Cross Publisher A"), "Cross Arena A")
		owner_b = make_customer("xb.tracer@example.com", "Xander B")
		make_publisher(owner_b, "Tracer Cross Publisher B")

		frappe.set_user(owner_b)
		with self.assertRaises(frappe.PermissionError):
			make_resource(venue_a)

	def test_publish_refuses_a_venue_with_no_resource(self):
		owner = make_customer("bare.tracer@example.com", "Bea Bare")
		venue = frappe.get_doc("Venue", make_venue(make_publisher(owner, "Tracer Bare Publisher"), "Bare Arena"))

		venue.status = "Published"
		self.assertRaises(frappe.ValidationError, venue.save)

	def test_publish_refuses_a_venue_whose_only_resource_is_inactive(self):
		owner = make_customer("idle.tracer@example.com", "Ida Idle")
		venue = make_venue(make_publisher(owner, "Tracer Idle Publisher"), "Idle Arena")
		make_resource(venue, status="Inactive")

		document = frappe.get_doc("Venue", venue)
		document.status = "Published"
		self.assertRaises(frappe.ValidationError, document.save)

	def test_publish_accepts_a_venue_with_a_bookable_resource(self):
		owner = make_customer("live.tracer@example.com", "Leo Live")
		venue = make_venue(make_publisher(owner, "Tracer Live Publisher"), "Live Arena")
		make_resource(venue)

		document = frappe.get_doc("Venue", venue)
		document.status = "Published"
		document.save()

		self.assertEqual(frappe.db.get_value("Venue", venue, "status"), "Published")

	def test_schedule_window_must_divide_into_whole_slots(self):
		owner = make_customer("partial.tracer@example.com", "Pat Partial")
		venue = make_venue(make_publisher(owner, "Tracer Partial Publisher"), "Partial Arena")

		with self.assertRaises(frappe.ValidationError):
			make_resource(venue, weekly_schedule=every_day("18:00:00", "22:30:00"))

	def test_schedule_closing_at_midnight_means_end_of_day(self):
		owner = make_customer("midnight.tracer@example.com", "Mia Midnight")
		venue = make_venue(make_publisher(owner, "Tracer Midnight Publisher"), "Midnight Arena")

		resource = make_resource(venue, weekly_schedule=every_day("18:00:00", "00:00:00"))

		self.assertTrue(resource)

	def test_overlapping_schedule_rows_are_refused(self):
		owner = make_customer("overlap.tracer@example.com", "Ola Overlap")
		venue = make_venue(make_publisher(owner, "Tracer Overlap Publisher"), "Overlap Arena")
		rows = [
			{"day_of_week": "Monday", "opens_at": "06:00:00", "closes_at": "12:00:00"},
			{"day_of_week": "Monday", "opens_at": "11:00:00", "closes_at": "15:00:00"},
		]

		with self.assertRaises(frappe.ValidationError):
			make_resource(venue, weekly_schedule=rows)

	def test_split_shifts_on_one_day_are_allowed(self):
		owner = make_customer("split.tracer@example.com", "Sid Split")
		venue = make_venue(make_publisher(owner, "Tracer Split Publisher"), "Split Arena")
		rows = [
			{"day_of_week": "Monday", "opens_at": "06:00:00", "closes_at": "12:00:00"},
			{"day_of_week": "Monday", "opens_at": "16:00:00", "closes_at": "23:00:00"},
		]

		self.assertTrue(make_resource(venue, weekly_schedule=rows))

	def test_search_venues_lists_published_venues_to_a_guest(self):
		"""D-34: publication is a property of the discovery query, not of a permission condition."""
		owner = make_customer("pub.tracer@example.com", "Pia Publish")
		venue = make_venue(make_publisher(owner, "Tracer Search Publisher"), "Searchable Arena")
		make_resource(venue)
		self._publish(venue)

		frappe.set_user("Guest")
		slugs = [row["slug"] for row in search_venues()]
		self.assertIn("searchable-arena", slugs)

	def test_search_venues_hides_unpublished_venues(self):
		owner = make_customer("draft.tracer@example.com", "Dara Draft")
		venue = make_venue(make_publisher(owner, "Tracer Draft Publisher"), "Draft Arena")
		make_resource(venue)

		frappe.set_user("Guest")
		self.assertNotIn("draft-arena", [row["slug"] for row in search_venues()])

	def test_search_venues_reports_the_lowest_price_and_resource_count(self):
		owner = make_customer("price.tracer@example.com", "Pim Price")
		venue = make_venue(make_publisher(owner, "Tracer Price Publisher"), "Priced Arena")
		make_resource(venue, "Turf A", base_price=250)
		make_resource(venue, "Turf B", base_price=180)
		self._publish(venue)

		frappe.set_user("Guest")
		row = next(row for row in search_venues() if row["slug"] == "priced-arena")
		self.assertEqual((row["from_price"], row["resource_count"]), (180, 2))

	def test_unique_index_exists(self):
		"""R1: the guarantee is the index. If the patch was skipped, say so loudly."""
		rows = frappe.db.sql(
			"""select 1 from information_schema.statistics
			where table_schema = database() and table_name = 'tabBooking Slot' and index_name = %s""",
			INDEX_NAME,
		)
		self.assertTrue(rows, "the Booking Slot unique index is missing")

	def test_grid_generation_counts_slots(self):
		resource = self._arena("grid")

		slots = get_day_grid(resource, tomorrow())

		self.assertEqual(len(slots), 4)
		self.assertEqual(slots[0]["start_time"], "18:00:00")
		self.assertEqual(slots[-1]["end_time"], "22:00:00")
		self.assertEqual({slot["price"] for slot in slots}, {250.0})

	def test_grid_marks_booked_from_ledger(self):
		"""A held slot reads `booked` to everyone but its owner — never `held`."""
		resource = self._arena("held")
		day = tomorrow()
		customer = make_customer("holder.tracer@example.com", "Hal Holder")
		create_booking(resource, day, "19:00:00", customer=customer)

		frappe.set_user(make_customer("looker.tracer@example.com", "Lou Looker"))
		statuses = {slot["start_time"]: slot["status"] for slot in get_day_grid(resource, day)}

		self.assertEqual(statuses["19:00:00"], "booked")
		self.assertEqual(statuses["20:00:00"], "available")

	def test_booking_holds_one_slot_for_ten_minutes(self):
		resource = self._arena("hold")
		day = tomorrow()
		customer = make_customer("hold.tracer@example.com", "Hana Hold")

		receipt = create_booking(resource, day, "19:00:00", customer=customer)

		booking = frappe.get_doc("Booking", receipt["booking"])
		self.assertEqual((booking.status, booking.line_count, booking.active_line_count), ("Pending Payment", 1, 1))
		self.assertEqual(booking.total_amount, 250.0)
		self.assertEqual(frappe.db.count("Booking Slot", {"booking": booking.name}), 1)
		held_for = (booking.hold_expires_at - utc_now()).total_seconds() / 60
		self.assertAlmostEqual(held_for, HOLD_MINUTES, delta=1)

	def test_line_utc_matches_venue_timezone(self):
		"""R2/I-9: the same wall clock in two venues is two different instants."""
		owner = make_customer("zones.tracer@example.com", "Zaid Zones")
		publisher = make_publisher(owner, "Tracer Zones Publisher")
		customer = make_customer("traveller.tracer@example.com", "Tia Traveller")
		day = tomorrow()

		instants = {
			timezone: self._book_at_seven(publisher, timezone, day, customer)
			for timezone in ("Asia/Dubai", "Asia/Kolkata")
		}

		self.assertEqual(str(instants["Asia/Dubai"]), f"{day} 15:00:00")
		self.assertEqual(str(instants["Asia/Kolkata"]), f"{day} 13:30:00")

	def test_booking_a_taken_slot_is_refused_with_the_conflict(self):
		resource = self._arena("taken")
		day = tomorrow()
		create_booking(resource, day, "19:00:00", customer=make_customer("first.tracer@example.com"))

		with self.assertRaises(SlotUnavailableError) as refusal:
			create_booking(resource, day, "19:00:00", customer=make_customer("second.tracer@example.com"))

		self.assertEqual(
			refusal.exception.conflicting_lines,
			[{"date": str(day), "start_time": "19:00:00", "reason": "booked"}],
		)

	def test_booking_a_slot_outside_the_schedule_is_refused(self):
		resource = self._arena("offgrid")

		with self.assertRaises(SlotUnavailableError) as refusal:
			create_booking(resource, tomorrow(), "09:00:00", customer=make_customer("early.tracer@example.com"))

		self.assertEqual(refusal.exception.conflicting_lines[0]["reason"], "off_grid")

	def test_duplicate_ledger_insert_rolls_back_booking(self):
		"""R1: a collision leaves no orphan Booking behind."""
		resource = self._arena("orphan")
		day = tomorrow()
		create_booking(resource, day, "19:00:00", customer=make_customer("keeper.tracer@example.com"))
		loser = make_customer("loser.tracer@example.com")

		with self.assertRaises(SlotUnavailableError):
			self._book_past_the_precheck(resource, day, loser)

		self.assertEqual(frappe.db.count("Booking", {"customer": loser}), 0)
		self.assertEqual(frappe.db.count("Booking Slot", {"resource": resource, "slot_date": day}), 1)

	def test_booking_is_visible_to_its_customer_and_the_publisher_only(self):
		"""I-8: the ledger is tenant data and the booking is also the customer's own."""
		resource = self._arena("privacy")
		owner = frappe.db.get_value("Bookable Resource", resource, "publisher")
		owner_user = frappe.get_doc("Publisher", owner).members[0].user
		customer = make_customer("mine.tracer@example.com", "Mia Mine")
		booking = create_booking(resource, tomorrow(), "19:00:00", customer=customer)["booking"]

		self.assertEqual(self._bookings_visible_to(customer), [booking])
		self.assertEqual(self._bookings_visible_to(owner_user), [booking])
		self.assertEqual(self._bookings_visible_to(make_customer("nosy.tracer@example.com")), [])

	def _bookings_visible_to(self, user: str) -> list[str]:
		frappe.set_user(user)
		visible = [row.name for row in frappe.get_list("Booking")]
		frappe.set_user("Administrator")
		return visible

	def _arena(self, prefix: str) -> str:
		"""A published venue with one resource open 18:00-22:00 at 60 minutes."""
		owner = make_customer(f"{prefix}.owner.tracer@example.com", "Ola Owner")
		publisher = make_publisher(owner, f"Tracer {prefix.title()} Publisher")
		venue = make_venue(publisher, f"Tracer {prefix.title()} Arena")
		resource = make_resource(venue)
		self._publish(venue)
		return resource

	def _book_at_seven(self, publisher: str, timezone: str, day, customer: str):
		frappe.set_user(frappe.get_doc("Publisher", publisher).members[0].user)
		venue = make_venue(publisher, f"Tracer {timezone} Arena", timezone=timezone)
		resource = make_resource(venue)
		booking = create_booking(resource, day, "19:00:00", customer=customer)["booking"]
		return frappe.get_doc("Booking", booking).lines[0].start_utc

	def _book_past_the_precheck(self, resource: str, day, customer: str):
		"""`claim` skips the courtesy pre-check, so the index itself has to do the refusing."""
		return BookingRequest(resource, [(day, to_time("19:00:00"))], customer).claim()

	def _publish(self, venue: str) -> None:
		document = frappe.get_doc("Venue", venue)
		document.status = "Published"
		document.save()


def tomorrow():
	return getdate(add_days(getdate(), 1))


def unused_venue_name() -> str:
	"""Slug assertions are exact, so they must not collide with whatever the site already holds."""
	return f"Tracer Arena {frappe.generate_hash(length=8)}"


class TestPayment(IntegrationTestCase):
	"""R5. One committed arena for the whole class: Frappe throttles user creation to 60 an
	hour, and a suite that signs a new customer up per assertion spends that budget on nothing."""

	_unused_days = itertools.count(1)

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.arena = make_committed_arena("payment", customers=2)
		cls.customer, cls.stranger = cls.arena.users[1], cls.arena.users[2]

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()  # the arena is dropped on another connection; this one must let go first
		drop_committed_arena(cls.arena)
		super().tearDownClass()

	def setUp(self):
		"""Every payment test starts where the pay page does: one live hold, on a date of its
		own. Frappe rolls a test class back as a unit, so two tests sharing a slot would
		collide on the ledger instead of on whatever they meant to prove."""
		super().setUp()
		clear_publisher_cache()
		frappe.set_user("Administrator")
		self.day = getdate(add_days(getdate(), next(self._unused_days)))
		self.booking = create_booking(self.arena.resource, self.day, "19:00:00", customer=self.customer)["booking"]
		frappe.set_user(self.customer)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_start_opens_a_hosted_checkout(self):
		"""R5: the SPA never builds a payment URL; the gateway hands one over."""
		opened = payment.start(self.booking)

		self.assertEqual(opened["redirect_url"], f"/apnaslot/pay/{opened['checkout_token']}")
		transaction = frappe.get_doc("Payment Transaction", {"checkout_token": opened["checkout_token"]})
		self.assertEqual((transaction.status, transaction.amount), ("Pending", 250.0))
		self.assertTrue(transaction.gateway_reference.startswith("MOCK-"))

	def test_start_reuses_a_live_transaction(self):
		"""A second checkout for the same hold would strand the first."""
		first = payment.start(self.booking)["checkout_token"]
		second = payment.start(self.booking)["checkout_token"]

		self.assertEqual(first, second)
		self.assertEqual(frappe.db.count("Payment Transaction", {"booking": self.booking}), 1)

	def test_get_checkout_refuses_someone_elses_token(self):
		"""The token is a bearer credential, so a wrong holder reads as 404, never 403."""
		token = payment.start(self.booking)["checkout_token"]

		frappe.set_user(self.stranger)
		with self.assertRaises(frappe.DoesNotExistError):
			payment.get_checkout(token)

	def test_callback_confirms_booking(self):
		"""**R5.** The signed callback drives the state machine; the ledger row stays put."""
		token = payment.start(self.booking)["checkout_token"]

		outcome = payment.simulate(token, SUCCEEDED)

		booking = frappe.get_doc("Booking", self.booking)
		self.assertEqual((outcome["status"], booking.status), ("Succeeded", "Confirmed"))
		self.assertIsNone(booking.hold_expires_at)
		self.assertEqual(frappe.db.count("Booking Slot", {"booking": booking.name}), 1)

	def test_callback_rejects_bad_signature(self):
		"""R5: a forged result is refused and the booking is untouched."""
		token = payment.start(self.booking)["checkout_token"]

		with self.assertRaises(frappe.PermissionError):
			payment.callback(token, SUCCEEDED, "not-the-signature")

		self.assertEqual(frappe.db.get_value("Booking", self.booking, "status"), "Pending Payment")
		self.assertEqual(frappe.db.count("Booking Slot", {"booking": self.booking}), 1)

	def test_callback_is_idempotent(self):
		"""A gateway that retries must not confirm, email or charge a second time."""
		token = payment.start(self.booking)["checkout_token"]

		first = payment.simulate(token, SUCCEEDED)
		second = payment.simulate(token, FAILED)

		self.assertEqual(first, second)
		self.assertEqual(frappe.db.get_value("Booking", self.booking, "status"), "Confirmed")
		self.assertEqual(frappe.db.count("Booking Slot", {"booking": self.booking}), 1)

	def test_payment_failure_releases_slot(self):
		"""R5: the slot is back on the grid on the next read, not on the next sweep."""
		token = payment.start(self.booking)["checkout_token"]

		payment.simulate(token, FAILED)

		booking = frappe.get_doc("Booking", self.booking)
		self.assertEqual((booking.status, booking.active_line_count), ("Payment Failed", 0))
		self.assertEqual(frappe.db.count("Booking Slot", {"booking": booking.name}), 0)
		statuses = {slot["start_time"]: slot["status"] for slot in get_day_grid(self.arena.resource, self.day)}
		self.assertEqual(statuses["19:00:00"], "available")

	def test_abandonment_leaves_the_hold_alone(self):
		"""D-16: only the timer releases a hold the customer walked away from."""
		token = payment.start(self.booking)["checkout_token"]

		payment.simulate(token, ABANDONED)

		self.assertEqual(frappe.db.get_value("Booking", self.booking, "status"), "Pending Payment")
		self.assertEqual(frappe.db.count("Booking Slot", {"booking": self.booking}), 1)

	def test_success_after_expiry_does_not_resurrect_the_booking(self):
		"""Expiry beats success: the slot may already belong to someone else."""
		token = payment.start(self.booking)["checkout_token"]
		release_booking(self.booking, "Expired")

		outcome = payment.simulate(token, SUCCEEDED)

		self.assertEqual(outcome["status"], "Succeeded")
		self.assertEqual(frappe.db.get_value("Booking", self.booking, "status"), "Expired")
		self.assertEqual(frappe.db.count("Booking Slot", {"booking": self.booking}), 0)

	def test_start_refuses_a_booking_that_is_no_longer_held(self):
		release_booking(self.booking, "Expired")

		with self.assertRaises(frappe.ValidationError):
			payment.start(self.booking)

	def test_release_booking_is_idempotent(self):
		"""R6 in miniature: a failed payment and the expiry job can race for one hold."""
		first = release_booking(self.booking, "Payment Failed")
		second = release_booking(self.booking, "Expired")

		self.assertEqual((first["released"], second["released"]), (1, 0))
		self.assertEqual(second["status"], "Payment Failed")


class TestLedgerRace(IntegrationTestCase):
	"""R1 lives in its own class on purpose. Frappe rolls a test class back as a unit, so a
	class that has already written holds naming-series locks its own second connection would
	then wait on. This class starts clean, which is what lets two real connections race."""

	def test_concurrent_booking_same_slot_one_wins(self):
		"""**The I-1 test.** Two connections past the pre-check, one slot: the database decides.
		One booking, one ledger row, one clean refusal."""
		arena = make_committed_arena("race")
		self.addCleanup(drop_committed_arena, arena)
		day = tomorrow()

		outcomes = self._race(arena, day)

		frappe.db.rollback()  # this connection reads nothing but its own snapshot until it ends
		receipts = [outcome for outcome in outcomes if isinstance(outcome, dict)]
		refusals = [outcome for outcome in outcomes if isinstance(outcome, SlotUnavailableError)]
		self.assertEqual(len(receipts), 1, f"expected exactly one winner, got {outcomes}")
		self.assertEqual(len(refusals), 1, f"expected exactly one clean refusal, got {outcomes}")
		self.assertEqual(frappe.db.count("Booking Slot", {"resource": arena.resource, "slot_date": day}), 1)
		self.assertEqual(frappe.db.count("Booking", {"resource": arena.resource}), 1)

	def _race(self, arena, day) -> list:
		outcomes: list = [None, None]
		gate = threading.Barrier(2)
		site = frappe.local.site
		threads = [
			threading.Thread(target=self._attempt, args=(site, arena, day, outcomes, index, gate))
			for index in range(2)
		]
		for thread in threads:
			thread.start()
		for thread in threads:
			thread.join(timeout=60)
		return outcomes

	def _book_past_the_precheck(self, resource: str, day, customer: str):
		"""`claim` skips the courtesy pre-check, so the index itself has to do the refusing."""
		return BookingRequest(resource, [(day, to_time("19:00:00"))], customer).claim()

	def _attempt(self, site, arena, day, outcomes: list, index: int, gate: threading.Barrier) -> None:
		"""Its own connection — two sequential calls would pass against no guarantee at all.
		`frappe.local` is thread-local, so the thread bootstraps itself from the site name."""
		frappe.init(site=site)
		frappe.connect()
		try:
			gate.wait()
			outcomes[index] = self._book_past_the_precheck(arena.resource, day, arena.users[index + 1])
			frappe.db.commit()
		except Exception as refusal:
			frappe.db.rollback()
			outcomes[index] = refusal
		finally:
			frappe.destroy()
