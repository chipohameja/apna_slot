import frappe
from frappe import _
from frappe.model.document import Document

from apna_slot.permissions import is_member_of
from apna_slot.utils.timezone import validate_timezone

POLICY_RANGES = {"max_advance_days": (1, 365), "min_lead_minutes": (0, 10080)}


class Venue(Document):
	def before_insert(self):
		self.slug = unique_slug(self.venue_name)
		self._inherit_from_publisher()

	def validate(self):
		self._check_publisher_is_mine()
		validate_timezone(self.timezone)
		self._check_policy_ranges()

	def before_save(self):
		if self.status == "Published":
			self._check_ready_to_publish()

	def _inherit_from_publisher(self):
		"""A venue is created in its publisher's locale. Currency is claimed rather than
		defaulted: Frappe seeds any field named `currency` from the site default (D-10)."""
		locale = frappe.db.get_value("Publisher", self.publisher, ["timezone", "currency"], as_dict=True)
		self.timezone = self.timezone or locale.timezone
		self.currency = locale.currency

	def _check_publisher_is_mine(self):
		if not is_member_of(self.publisher):
			frappe.throw(_("You are not a member of {0}").format(self.publisher), frappe.PermissionError)

	def _check_policy_ranges(self):
		for fieldname, (low, high) in POLICY_RANGES.items():
			value = self.get(fieldname)
			if value is None or not low <= value <= high:
				label = _(self.meta.get_label(fieldname))
				frappe.throw(_("{0} must be between {1} and {2}").format(label, low, high))

	def _check_ready_to_publish(self):
		"""A published venue nobody can book is worse than an unpublished one."""
		if self.is_new() or not frappe.db.exists("Bookable Resource", {"venue": self.name}):
			frappe.throw(_("Add a bookable resource before publishing {0}").format(self.venue_name))
		if not self._bookable_resources():
			frappe.throw(
				_("{0} has no active resource with both opening hours and a price above zero").format(
					self.venue_name
				)
			)

	def _bookable_resources(self) -> list[str]:
		names = frappe.get_all(
			"Bookable Resource",
			filters={"venue": self.name, "status": "Active", "base_price": (">", 0)},
			pluck="name",
		)
		return [name for name in names if frappe.db.count("Resource Schedule Row", {"parent": name})]


def unique_slug(venue_name: str) -> str:
	"""Changing a live URL breaks every shared link, so a slug is claimed once and kept."""
	base = frappe.scrub(venue_name).replace("_", "-")
	slug, suffix = base, 2
	while frappe.db.exists("Venue", {"slug": slug}):
		slug, suffix = f"{base}-{suffix}", suffix + 1
	return slug
