import frappe

PUBLISHER_CACHE_KEY = "apna_slot_publishers"


def get_user_publishers(user: str | None = None) -> list[str]:
	"""Publisher names the user is a member of. Empty for Guest, cached per user."""
	user = user or frappe.session.user
	if user == "Guest":
		return []
	cached = frappe.cache.hget(PUBLISHER_CACHE_KEY, user)
	if cached is not None:
		return cached
	publishers = _fetch_memberships(user)
	frappe.cache.hset(PUBLISHER_CACHE_KEY, user, publishers)
	return publishers


def clear_publisher_cache(user: str | None = None) -> None:
	if user:
		frappe.cache.hdel(PUBLISHER_CACHE_KEY, user)
	else:
		frappe.cache.delete_key(PUBLISHER_CACHE_KEY)


def publisher_query(user: str | None = None, doctype: str | None = None) -> str:
	"""Row-level scope for the Publisher doctype itself."""
	return scope_condition("`tabPublisher`.name", user)


def publisher_has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
	return is_member_of(doc.name, user)


def tenant_query(user: str | None = None, doctype: str | None = None) -> str:
	"""Row-level scope for any doctype carrying a `publisher` link field."""
	return scope_condition(f"`tab{doctype}`.publisher", user)


def tenant_has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
	return is_member_of(publisher_of(doc), user)


def booking_query(user: str | None = None, doctype: str | None = None) -> str:
	"""A booking belongs to its customer as well as to the owning publisher (I-8)."""
	user = user or frappe.session.user
	tenant = scope_condition("`tabBooking`.publisher", user)
	if not tenant:
		return ""
	own = f"`tabBooking`.customer = {frappe.db.escape(user)}"
	return own if tenant == "1=0" else f"({tenant} or {own})"


def booking_has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
	user = user or frappe.session.user
	return doc.get("customer") == user or tenant_has_permission(doc, ptype, user)


def publisher_of(doc) -> str | None:
	"""The tenant a document belongs to. Frappe checks create permission before `fetch_from`
	denormalises `publisher`, so a new document resolves through whatever link it does carry."""
	if doc.get("publisher"):
		return doc.get("publisher")
	for doctype, fieldname in (("Venue", "venue"), ("Bookable Resource", "resource"), ("Booking", "booking")):
		parent = doc.get(fieldname)
		if parent:
			return frappe.db.get_value(doctype, parent, "publisher")
	return None


def scope_condition(column: str, user: str | None = None) -> str:
	"""Fail closed: no membership matches no rows, never every row."""
	if is_platform_admin(user):
		return ""
	publishers = get_user_publishers(user)
	if not publishers:
		return "1=0"
	names = ", ".join(frappe.db.escape(name) for name in publishers)
	return f"{column} in ({names})"


def is_member_of(publisher: str | None, user: str | None = None) -> bool:
	if is_platform_admin(user):
		return True
	return bool(publisher) and publisher in get_user_publishers(user)


def is_platform_admin(user: str | None = None) -> bool:
	user = user or frappe.session.user
	return user == "Administrator" or "System Manager" in frappe.get_roles(user)


def _fetch_memberships(user: str) -> list[str]:
	return frappe.get_all(
		"Publisher Member",
		filters={"user": user, "parenttype": "Publisher"},
		pluck="parent",
	)
