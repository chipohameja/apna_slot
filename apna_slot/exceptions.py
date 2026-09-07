import frappe
from frappe import _
from frappe.utils import formatdate


class SlotUnavailableError(frappe.ValidationError):
	"""Someone else holds a requested slot. Carries the lines the grid must re-render."""

	http_status_code = 409

	def __init__(self, conflicting_lines: list[dict]):
		self.conflicting_lines = conflicting_lines
		super().__init__(describe_conflicts(conflicting_lines))


def refuse_slots(conflicting_lines: list[dict]) -> None:
	"""Raise the 409. Thrown rather than raised because only `frappe.throw` puts the message in
	the response — a bare `raise` sends the browser the exception class name and nothing else."""
	frappe.throw(describe_conflicts(conflicting_lines), exc=SlotUnavailableError(conflicting_lines))


def describe_conflicts(conflicting_lines: list[dict]) -> str:
	first = conflicting_lines[0]
	taken = _("{0} on {1} is no longer available. Pick another slot.").format(
		first["start_time"][:5], formatdate(first["date"], "d MMM")
	)
	others = len(conflicting_lines) - 1
	return taken if not others else f"{taken} {_('{0} more of your slots have gone too.').format(others)}"
