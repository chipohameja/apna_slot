import frappe
from frappe import _


@frappe.whitelist(methods=["POST"])
def create_publisher(publisher_name: str, contact_email: str, currency: str, timezone: str) -> dict:
	"""Create the caller's business, with the caller as its Owner."""
	_refuse_second_business()
	values = {
		"publisher_name": publisher_name,
		"contact_email": contact_email,
		"currency": currency,
		"timezone": timezone,
	}
	publisher = _insert_owned_by_caller(values)
	return {"name": publisher.name, "publisher_name": publisher.publisher_name, "member_role": "Owner"}


def memberships_for(user: str) -> list[dict]:
	"""Every publisher the user belongs to, with the role they hold in it."""
	rows = frappe.get_all(
		"Publisher Member",
		filters={"user": user, "parenttype": "Publisher"},
		fields=["parent", "member_role"],
	)
	roles = {row.parent: row.member_role for row in rows}
	return [_with_role(publisher, roles) for publisher in _publishers(list(roles))]


def _publishers(names: list[str]) -> list[dict]:
	if not names:
		return []
	return frappe.get_all(
		"Publisher",
		filters={"name": ("in", names)},
		fields=["name", "publisher_name", "currency", "timezone", "status"],
		order_by="creation asc",
	)


def _with_role(publisher: dict, roles: dict) -> dict:
	publisher["member_role"] = roles[publisher["name"]]
	return publisher


def _refuse_second_business() -> None:
	owned = [row for row in memberships_for(frappe.session.user) if row["member_role"] == "Owner"]
	if owned:
		frappe.throw(_("You already own {0}").format(owned[0]["publisher_name"]))


def _insert_owned_by_caller(values: dict):
	"""The caller holds no publisher role yet — creating this record is what grants it."""
	publisher = frappe.new_doc("Publisher")
	publisher.update(values)
	publisher.append("members", {"user": frappe.session.user, "member_role": "Owner"})
	publisher.insert(ignore_permissions=True)
	return publisher
