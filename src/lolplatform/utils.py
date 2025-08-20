from datetime import datetime, timedelta

def parse_date_flexible(date_str):
    formats = [
        '%Y-%m-%d',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(date_str)
    except Exception:
        raise ValueError(f"Date string '{date_str}' is not in a recognized format")

def generate_date_tuples(start_time, end_date=None):
    start_date = parse_date_flexible(start_time)

    # Use given end_date if provided, else default to today
    if end_date is not None:
        end_date = parse_date_flexible(end_date)
    else:
        end_date = datetime.today()

    date_tuples = []

    while start_date < end_date:
        next_date = min(start_date + timedelta(days=5), end_date)
        date_tuples.append((start_date.strftime('%Y-%m-%d'), next_date.strftime('%Y-%m-%d')))
        start_date = next_date

    return date_tuples