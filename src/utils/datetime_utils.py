from datetime import datetime, timedelta, timezone


def move_days_from_now(days: int, backward: bool = True, milli_sec: bool = True) -> int:
    """
    Move forward or backward a specific number of days from the current date
    and return a rounded timestamp.
    Args:
        days (int): Number of days to move. Should be positive.
        backward: True to move backward in time, False to move forward
        milli_sec: True if convert the result from sec >> milli_sec
    Returns:
        int: Rounded timestamp in seconds since epoch
    """
    current_time = datetime.now()

    if backward:
        target_date = current_time - timedelta(days=days)
    else:
        target_date = current_time + timedelta(days=days)

    # Convert to timestamp and round to nearest second
    timestamp = int(target_date.timestamp())

    return timestamp * 1000 if milli_sec else timestamp


def convert_strtime(str_time: str | float):
    """Interpret input as UTC and return POSIX timestamp."""
    dt_obj = datetime.strptime(str_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return dt_obj.timestamp()


def convert_timestamp(timestamp: float | int):
    """Convert POSIX timestamp to UTC string (no +00:00 in output)."""
    dt_utc = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return dt_utc.strftime("%Y-%m-%d %H:%M:%S")


def pretty_time(seconds):
    sign_string = "-" if seconds < 0 else ""
    seconds = abs(int(seconds))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days > 0:
        return "%s%dd%dh%dm%ds" % (sign_string, days, hours, minutes, seconds)
    elif hours > 0:
        return "%s%dh%dm%ds" % (sign_string, hours, minutes, seconds)
    elif minutes > 0:
        return "%s%dm%ds" % (sign_string, minutes, seconds)
    else:
        return "%s%ds" % (sign_string, seconds)
