import frappe
from frappe.tests import IntegrationTestCase

from apna_slot.api.auth import CUSTOMER_ROLE, get_session_user
from apna_slot.api.discovery import search_venues
from apna_slot.apna_slot_core.doctype.publisher.publisher import PUBLISHER_ROLE
from apna_slot.permissions import clear_publisher_cache, publisher_query
from apna_slot.tests.fixtures import (
	every_day,
	make_customer,
	make_publisher,
	make_resource,
	make_venue,
)
from apna_slot.utils.roles import grant_role


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

	def _publish(self, venue: str) -> None:
		document = frappe.get_doc("Venue", venue)
		document.status = "Published"
		document.save()


def unused_venue_name() -> str:
	"""Slug assertions are exact, so they must not collide with whatever the site already holds."""
	return f"Tracer Arena {frappe.generate_hash(length=8)}"
