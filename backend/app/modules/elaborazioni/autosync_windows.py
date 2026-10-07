from datetime import datetime, time, timedelta


def window_context(local_now: datetime, windows: str) -> tuple[bool, str]:
    current_time = local_now.time()
    current_date = local_now.date()
    for interval in windows.split(","):
        start_text, end_text = interval.split("-")
        start, end = time.fromisoformat(start_text), time.fromisoformat(end_text)
        if start == end or start <= current_time < end:
            return True, current_date.isoformat()
        if start > end:
            if current_time >= start:
                return True, current_date.isoformat()
            if current_time < end:
                return True, (current_date - timedelta(days=1)).isoformat()
    return False, current_date.isoformat()
