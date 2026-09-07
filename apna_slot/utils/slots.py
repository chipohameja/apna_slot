from datetime import timedelta

DAY_END_MINUTES = 24 * 60


def to_minutes(value: timedelta | str) -> int:
	"""Minutes since midnight. Frappe hands Time fields over as timedelta or as a string."""
	if isinstance(value, timedelta):
		return int(value.total_seconds() // 60)
	hours, minutes, *_ = str(value).split(":")
	return int(hours) * 60 + int(minutes)


def span_minutes(opens_at: timedelta | str, closes_at: timedelta | str) -> int:
	"""Length of one opening window; a close of 00:00 means end of day (24:00)."""
	return (to_minutes(closes_at) or DAY_END_MINUTES) - to_minutes(opens_at)
