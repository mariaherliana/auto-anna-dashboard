from config import CONFIG
from src.csv_processing import (
    process_dashboard_csv,
    save_merged_csv,
)


def __main__():
    print("Starting Auto-Anna (Dashboard Only)")
    for files in CONFIG:
        print(f"> Processing dashboard file for client {files.client}")
        call_details = process_dashboard_csv(
            files.dashboard, files.carrier, client=files.client
        )
        save_merged_csv(call_details, files.output)
    print("All files processed successfully")


__main__()
