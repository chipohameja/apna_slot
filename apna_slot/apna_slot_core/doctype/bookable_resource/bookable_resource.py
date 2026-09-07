import frappe
from frappe import _
from frappe.model.document import Document

from apna_slot.utils.slots import span_minutes, to_minutes

CAP_RANGES = {"max_slots_per_booking": (1, 12), "max_dates_per_booking": (1, 26)}


class BookableResource(Document):
	def validate(self):
		self._check_cap_ranges()
		self._check_rows_partition_into_slots()
		self._check_rows_do_not_overlap()

	@property
	def slot_minutes(self) -> int:
		return int(self.slot_duration_minutes)

	def _check_cap_ranges(self):
		for fieldname, (low, high) in CAP_RANGES.items():
			value = self.get(fieldname)
			if value is None or not low <= value <= high:
				label = _(self.meta.get_label(fieldname))
				frappe.throw(_("{0} must be between {1} and {2}").format(label, low, high))

	def _check_rows_partition_into_slots(self):
		for row in self.weekly_schedule:
			self._check_row(row)

	def _check_row(self, row):
		span = span_minutes(row.opens_at, row.closes_at)
		if span <= 0:
			frappe.throw(_("Row {0}: {1} closes before it opens").format(row.idx, row.day_of_week))
		remainder = span % self.slot_minutes
		if remainder:
			frappe.throw(
				_("Row {0}: {1} is open for {2} minutes, which is {3} short of a whole {4}-minute slot").format(
					row.idx, row.day_of_week, span, self.slot_minutes - remainder, self.slot_minutes
				)
			)

	def _check_rows_do_not_overlap(self):
		for day, windows in self._windows_by_day().items():
			self._check_day(day, windows)

	def _windows_by_day(self) -> dict[str, list[tuple[int, int]]]:
		days: dict[str, list[tuple[int, int]]] = {}
		for row in self.weekly_schedule:
			opens = to_minutes(row.opens_at)
			days.setdefault(row.day_of_week, []).append((opens, opens + span_minutes(row.opens_at, row.closes_at)))
		return days

	def _check_day(self, day: str, windows: list[tuple[int, int]]):
		windows.sort()
		for (_opens, closes), (next_opens, _next_closes) in zip(windows, windows[1:], strict=False):
			if next_opens < closes:
				frappe.throw(_("Two {0} rows overlap").format(day))
