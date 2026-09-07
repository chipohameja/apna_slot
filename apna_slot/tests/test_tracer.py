import frappe
from frappe.tests import IntegrationTestCase

from apna_slot.api.auth import CUSTOMER_ROLE, get_session_user
from apna_slot.apna_slot_core.doctype.publisher.publisher import PUBLISHER_ROLE
from apna_slot.permissions import clear_publisher_cache, publisher_query
from apna_slot.tests.fixtures import make_customer, make_publisher
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
