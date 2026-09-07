import frappe

INDEX_NAME = "unique_resource_slot"


def execute():
	"""The double-booking guarantee (I-1, D-17). DDL no ORM expresses; never drop it."""
	if _index_exists():
		return
	frappe.db.sql(
		"""
		ALTER TABLE `tabBooking Slot`
		ADD UNIQUE INDEX `unique_resource_slot` (`resource`, `slot_date`, `start_time`)
		"""
	)


def _index_exists() -> bool:
	return bool(
		frappe.db.sql(
			"""
			select 1 from information_schema.statistics
			where table_schema = database()
			  and table_name = 'tabBooking Slot'
			  and index_name = %s
			limit 1
			""",
			INDEX_NAME,
		)
	)
