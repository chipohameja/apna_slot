import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import escape_html

from apna_slot.api.publisher import memberships_for
from apna_slot.utils.roles import grant_role

CUSTOMER_ROLE = "Apna Slot Customer"


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=60 * 60)
def sign_up(email: str, full_name: str, password: str, phone: str | None = None) -> dict:
	"""Create a customer account and log it in."""
	if frappe.db.exists("User", {"email": email}):
		frappe.throw(_("Could not create that account. Try logging in instead."))
	user = _create_customer(email, full_name, password, phone)
	_start_session(user.name)
	return {"user": user.name}


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_session_user() -> dict:
	"""The SPA's bootstrap payload."""
	user = frappe.session.user
	if user == "Guest":
		return {"user": user, "full_name": "Guest", "is_guest": True, "roles": [], "publishers": []}
	return {
		"user": user,
		"full_name": frappe.db.get_value("User", user, "full_name"),
		"is_guest": False,
		"roles": frappe.get_roles(user),
		"publishers": memberships_for(user),
	}


def _create_customer(email: str, full_name: str, password: str, phone: str | None):
	"""Website User creation is privileged; the account belongs to nobody until it exists."""
	user = frappe.new_doc("User")
	user.update(
		{
			"email": email,
			"first_name": escape_html(full_name),
			"mobile_no": phone,
			"user_type": "Website User",
			"send_welcome_email": 0,
			"new_password": password,
		}
	)
	user.insert(ignore_permissions=True)
	grant_role(user.name, CUSTOMER_ROLE)
	return user


def _start_session(user: str) -> None:
	login_manager = getattr(frappe.local, "login_manager", None)
	if login_manager:
		login_manager.login_as(user)
	else:
		frappe.set_user(user)
