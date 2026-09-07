import frappe


def grant_role(user: str, role: str) -> None:
	"""Add a role to a user; a privileged act, so it ignores the caller's permissions."""
	document = frappe.get_doc("User", user)
	if role in {row.role for row in document.roles}:
		return
	document.flags.ignore_permissions = True
	document.add_roles(role)
