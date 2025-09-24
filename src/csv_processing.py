from typing import Optional
import pandas as pd
from src.CallDetail import CallDetail
import math


def process_dashboard_csv(
    file_path: str, carrier: str, call_details: Optional[dict[str, CallDetail]] = None, client: str = ""
) -> dict[str, CallDetail]:
    if call_details is None:
        call_details = {}

    print(f"- Reading dashboard file {file_path}...")
    df1 = pd.read_csv(file_path, low_memory=False).astype(str)

    for index, row in df1.iterrows():
        call_detail = CallDetail(
            client=client,
            sequence_id=row["Sequence ID"],
            user_name=row["User name"],
            call_from=row["Call from"],
            call_to=row["Call to"],
            call_type=row["Call type"],
            dial_start_at=row["Dial begin time"],
            dial_answered_at=row["Call begin time"],
            dial_end_at=row["Call end time"],
            ringing_time=row["Ringing time"],
            call_duration=row["Call duration"],
            call_memo=row["Call memo"],
            carrier=carrier,
        )

        key = call_detail.hash_key()
        if key in call_details:
            # Update existing entry if already present
            existing_call_detail = call_details[key]
            existing_call_detail.user_name = row["User name"]
            existing_call_detail.call_memo = row["Call memo"]
        else:
            call_details[key] = call_detail

    return call_details


def round_up_duration_minutes(call_duration: str) -> int:
    try:
        if ":" in call_duration:
            h, m, s = map(int, call_duration.split(":"))
            total_minutes = h * 60 + m + math.ceil(s / 60)
        else:
            total_minutes = math.ceil(int(call_duration) / 60)  # Assume it's in seconds
        return total_minutes
    except Exception as e:
        print(f"Error parsing call duration (minutes): {call_duration}, Error: {e}")
        return 0


def round_up_duration_seconds(call_duration: str) -> int:
    try:
        if ":" in call_duration:
            h, m, s = map(int, call_duration.split(":"))
            total_seconds = h * 3600 + m * 60 + s
        else:
            total_seconds = int(call_duration)  # Already in seconds
        return total_seconds
    except Exception as e:
        print(f"Error parsing call duration (seconds): {call_duration}, Error: {e}")
        return 0


def save_merged_csv(call_details: dict[str, "CallDetail"], output_path: str) -> None:
    print("- Saving merged CSV file...")
    call_details_list = []
    for key, value in call_details.items():
        call_dict = value.to_dict()
        call_dict["Round up duration (minutes)"] = round_up_duration_minutes(call_dict["Call duration"])
        call_dict["Round up duration (seconds)"] = round_up_duration_seconds(call_dict["Call duration"])
        call_details_list.append(call_dict)
    
    df = pd.DataFrame(call_details_list)
    df.to_csv(output_path, index=False)
