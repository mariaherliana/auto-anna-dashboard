from datetime import datetime, timedelta, timezone
from typing import Optional

from src.idn_area_codes import EMERGENCY_NUMBERS, PHONE_PREFIXES, INTERNATIONAL_PHONE_PREFIXES

SPECIAL_PREFIXES = [211500, 211400, 21150, 21140, 1500, 1400, 800, 84, 31, 21, 8]

def call_hash(call_from: int, call_to: int, dial_start_at: datetime) -> str:
    return f"{call_from}_{call_to}_{dial_start_at}".replace(" ", "_")

def convert_to_jakarta_time_iso(original_date_str: str, region: str) -> datetime:
    if region != "jkt":
        raise Exception(
            "Timezone not supported. Only Jakarta time is supported for now."
        )

    # Parse the original date string in UTC time
    original_date = datetime.strptime(original_date_str, "%Y-%m-%d %H:%M:%S")
    utc_timezone = timezone.utc
    original_date_utc = original_date.replace(tzinfo=utc_timezone)

    # Add 7 hours to the original date to convert it to Jakarta time
    jakarta_offset = timedelta(hours=7)
    jakarta_date = original_date_utc + jakarta_offset
    jakarta_date = jakarta_date.replace(tzinfo=timezone(timedelta(hours=7)))
    return jakarta_date

import phonenumbers

def parse_phone_number(phone_number: int | str) -> int | str:
    # If the phone number is an integer, return it directly
    if isinstance(phone_number, int):
        return phone_number

    # If phone_number is "scancall", return as it is
    if phone_number == "scancall":
        return "scancall"

    # Clean the number by removing +, hyphens, parentheses, and spaces
    cleaned_number = phone_number.replace("+", "").replace("-", "").replace("(", "").replace(")", "").replace(" ", "")

    # Remove country code 62 if present
    if cleaned_number.startswith("62"):
        cleaned_number = cleaned_number[2:]

    # Try to convert to an integer
    try:
        return int(cleaned_number)
    except ValueError:
        return cleaned_number

def classify_number(phone_number: int, call_type: str, call_from: str, call_to: str) -> str:
    phone_number_str = str(phone_number)

    # Classify based on call type
    if call_type in ["Internal Call", "EXTENSION"]:
        return "Internal Call"
    if call_type == "Internal Call (No answer)":
        return "Internal Call (No answer)"
    if call_type == "AUTOMATIC_RECORD":
        return "Voicemail"
    if call_type == "AUTOMATIC_TRANSFER":
        return "Automatic Transfer"
    if call_type == "Monitoring":
        return "Monitoring"
    if call_from == "scancall":
        return "scancall"
    if call_type == "Call transfer" and len(str(call_from)) == 3 and str(call_from).isdigit():
        return "Internal Call"

    # Check if the number is an emergency number (3, 4, or 5 digits)
    if len(phone_number_str) in [3, 4, 5]:
        classification = EMERGENCY_NUMBERS.get(phone_number)
        if classification:
            return classification

    # Sort prefixes by length in descending order for matching
    sorted_prefixes = sorted(map(str, PHONE_PREFIXES.keys()), key=len, reverse=True)

    # Check for phone prefixes
    for prefix in sorted_prefixes:
        if phone_number_str.startswith(prefix):
            return PHONE_PREFIXES.get(int(prefix))

    # Check against special prefixes
    for prefix in SPECIAL_PREFIXES:
        if phone_number_str.startswith(str(prefix)):
            return PHONE_PREFIXES.get(prefix)

    # Check against international prefixes
    for prefix, country in INTERNATIONAL_PHONE_PREFIXES.items():
        if phone_number_str.startswith(str(prefix).replace("+", "")):
            return f"International - {country}"

    return "Unknown number type"

def format_datetime_as_human_readable(datetime_object: Optional[datetime]) -> str:
    return datetime_object.strftime("%Y-%m-%d %H:%M:%S") if datetime_object else "-"

def format_datetime_as_iso(datetime_object: datetime) -> str: 
    return str(datetime_object).replace(" ", "T")

def format_timedelta(time_duration: timedelta) -> str:
    time_duration_str = str(time_duration)
    time_parts = time_duration_str.split(", ")
    time_str = time_parts[-1]
    return time_str

def format_username(user_name: str) -> str:
    return user_name if user_name else "-"

def parse_call_memo(memo: str) -> str:
    if memo == "" or memo == "nan":
        return "-"
    return memo

def parse_iso_datetime(datetime_str: str) -> datetime:
    return datetime.fromisoformat(datetime_str)

def parse_jakarta_datetime(datetime_str: str, region: str) -> str:
    if datetime_str == "nan":
        return "-"
    jakarta_iso_date = convert_to_jakarta_time_iso(datetime_str, region)
    return format_datetime_as_iso(jakarta_iso_date)

def parse_time_duration(time_duration_string: str) -> timedelta:
    hours, minutes, seconds = time_duration_string.split(":")
    return timedelta(hours=int(hours), minutes=int(minutes), seconds=int(seconds))