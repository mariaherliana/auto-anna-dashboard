from typing import Optional
import pandas as pd
import math
from src.CallDetail import CallDetail
from src.FileConfig import Files


def process_dashboard_csv(
    config: Files,
    call_details: Optional[dict[str, CallDetail]] = None
) -> dict[str, CallDetail]:
    """
    Process a dashboard CSV file and return a dictionary of CallDetail objects.

    Args:
        config (Files): Configuration object with client, dashboard path, carrier, and rates.
        call_details (Optional[dict[str, CallDetail]]): Existing dictionary of call details.

    Returns:
        dict[str, CallDetail]: Processed call details keyed by hash.
    """
    if call_details is None:
        call_details = {}

    print(f"- Reading dashboard file {config.dashboard}...")
    df = pd.read_csv(config.dashboard, low_memory=False).astype(str)

    for _, row in df.iterrows():
        call_detail = CallDetail(
            client=config.client,
            sequence_id=row.get("Sequence ID", ""),
            user_name=row.get("User name", ""),
            call_from=row.get("Call from", ""),
            call_to=row.get("Call to", ""),
            call_type=row.get("Call type", ""),
            dial_start_at=row.get("Dial begin time", ""),
            dial_answered_at=row.get("Call begin time", ""),
            dial_end_at=row.get("Call end time", ""),
            ringing_time=row.get("Ringing time", ""),
            call_duration=row.get("Call duration", ""),
            call_memo=row.get("Call memo", ""),
            carrier=config.carrier,
            config=config,
        )

        key = call_detail.hash_key()
        if key in call_details:
            # Update existing entry if already present
            existing = call_details[key]
            existing.user_name = row.get("User name", "")
            existing.call_memo = row.get("Call memo", "")
        else:
            call_details[key] = call_detail

    return call_details


def round_up_duration_minutes(call_duration: str) -> int:
    """
    Round up call duration string to minutes.
    Supports both HH:MM:SS and raw seconds.
    """
    try:
        if ":" in call_duration:
            h, m, s = map(int, call_duration.split(":"))
            return h * 60 + m + math.ceil(s / 60)
        return math.ceil(int(call_duration) / 60)
    except Exception as e:
        print(f"Error parsing call duration (minutes): {call_duration}, Error: {e}")
        return 0


def round_up_duration_seconds(call_duration: str) -> int:
    """
    Convert call duration string to total seconds.
    Supports both HH:MM:SS and raw seconds.
    """
    try:
        if ":" in call_duration:
            h, m, s = map(int, call_duration.split(":"))
            return h * 3600 + m * 60 + s
        return int(call_duration)
    except Exception as e:
        print(f"Error parsing call duration (seconds): {call_duration}, Error: {e}")
        return 0


def save_merged_csv(call_details: dict[str, CallDetail], output_path: str) -> None:
    """
    Save merged call details to a CSV file, including rounded durations.
    """
    print(f"- Saving merged CSV file to {output_path}...")
    call_details_list = []

    for _, detail in call_details.items():
        call_dict = detail.to_dict()
        call_dict["Round up duration (minutes)"] = round_up_duration_minutes(call_dict["Call duration"])
        call_dict["Round up duration (seconds)"] = round_up_duration_seconds(call_dict["Call duration"])
        call_details_list.append(call_dict)

    df = pd.DataFrame(call_details_list)
    df.to_csv(output_path, index=False)
