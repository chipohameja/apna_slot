import frappe
from frappe import _
from frappe.model.document import Document

from apna_slot.permissions import clear_publisher_cache
from apna_slot.utils.roles import grant_role
from apna_slot.utils.timezone import validate_timezone

PUBLISHER_ROLE = "Apna Slot Publisher"


class Publisher(Document):
	def validate(self):
		validate_timezone(self.timezone)
		self._check_name_is_free()
		self._check_members_are_unique()
		self._check_has_an_owner()

	def before_insert(self):
		if not self._rows_for(frappe.session.user):
			self.append("members", {"user": frappe.session.user, "member_role": "Owner"})

	def after_insert(self):
		self._grant_publisher_role()
		clear_publisher_cache()

	def on_update(self):
		self._grant_publisher_role()
		clear_publisher_cache()

	def on_trash(self):
		clear_publisher_cache()

	def member_role_of(self, user: str) -> str | None:
		rows = self._rows_for(user)
		return rows[0].member_role if rows else None

	def _rows_for(self, user: str) -> list:
		return [row for row in self.members if row.user == user]

	def _check_name_is_free(self):
		taken = frappe.db.exists("Publisher", {"publisher_name": self.publisher_name, "name": ("!=", self.name)})
		if taken:
			frappe.throw(_("{0} is already listed. Choose another business name.").format(self.publisher_name))

	def _check_members_are_unique(self):
		users = [row.user for row in self.members]
		duplicates = {user for user in users if users.count(user) > 1}
		if duplicates:
			frappe.throw(_("{0} is listed as a member twice").format(", ".join(sorted(duplicates))))

	def _check_has_an_owner(self):
		if not any(row.member_role == "Owner" for row in self.members):
			frappe.throw(_("A publisher needs at least one member with the Owner role"))

	def _grant_publisher_role(self):
		for row in self.members:
			grant_role(row.user, PUBLISHER_ROLE)
