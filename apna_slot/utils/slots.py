from datetime import time, timedelta

DAY_END_MINUTES = 24 * 60


def to_time(value: timedelta | time | str) -> time:
	"""Frappe hands Time fields over as timedelta, as a string, or already as a time."""
	if isinstance(value, time):
		return value
	return minutes_to_time(to_minutes(value))


def to_minutes(value: timedelta | time | str) -> int:
	"""Minutes since midnight."""
	if isinstance(value, timedelta):
		return int(value.total_seconds() // 60)
	if isinstance(value, time):
		return value.hour * 60 + value.minute
	hours, minutes, *_ = str(value).split(":")
	return int(hours) * 60 + int(minutes)


def minutes_to_time(minutes: int) -> time:
	"""24:00 is the end of a day, not a time of day, so it wraps to 00:00."""
	return time(hour=minutes // 60 % 24, minute=minutes % 60)


def span_minutes(opens_at, closes_at) -> int:
	"""Length of one opening window; a close of 00:00 means end of day (24:00)."""
	return (to_minutes(closes_at) or DAY_END_MINUTES) - to_minutes(opens_at)


def slot_starts(opens_at, closes_at, slot_minutes: int) -> list[time]:
	"""Every slot start in one opening window, stepping by the slot length."""
	opens = to_minutes(opens_at)
	return [minutes_to_time(start) for start in range(opens, opens + span_minutes(opens_at, closes_at), slot_minutes)]


def add_minutes(start: time, minutes: int) -> time:
	return minutes_to_time(to_minutes(start) + minutes)
