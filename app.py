# app.py
import streamlit as st
import pandas as pd
import tempfile
import os
import uuid
from datetime import datetime, date
from typing import List, Dict, Any
from src.csv_processing import process_dashboard_csv, save_merged_csv
from src.FileConfig import Files

# ------------------------
# Page Setup
# ------------------------
st.set_page_config(
    page_title="MiiTel CC Calculator",
    page_icon="📞",
    layout="wide",
)

# ------------------------
# Directories
# ------------------------
PROCESSED_DIR = "processed_files"
LOGS_DIR = os.path.join(PROCESSED_DIR, "logs")
CDR_DIR = os.path.join(PROCESSED_DIR, "cdr_requests")
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(CDR_DIR, exist_ok=True)

# ------------------------
# Helpers — monthly log filenames
# ------------------------
def month_key_from_date(d: datetime = None) -> str:
    d = d or datetime.now()
    return d.strftime("%Y_%m")

def processing_log_file_for(month_key: str) -> str:
    return os.path.join(LOGS_DIR, f"processing_logs_{month_key}.csv")

def cdr_log_file_for(month_key: str) -> str:
    return os.path.join(CDR_DIR, f"cdr_requests_{month_key}.csv")

# ------------------------
# Persistence helpers
# ------------------------
def append_row_to_csv(file_path: str, row: Dict[str, Any]) -> None:
    df = pd.DataFrame([row])
    if os.path.exists(file_path):
        df.to_csv(file_path, mode="a", header=False, index=False)
    else:
        df.to_csv(file_path, index=False)

def load_csv_as_records(file_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(file_path):
        return []
    df = pd.read_csv(file_path)
    return df.to_dict(orient="records")

def write_records_to_csv(file_path: str, records: List[Dict[str, Any]]) -> None:
    df = pd.DataFrame(records)
    df.to_csv(file_path, index=False)

# ------------------------
# Processing logs
# ------------------------
def add_processing_log(client: str, original_file_name: str, processed_file_path: str, status: str = "Processed"):
    month_key = month_key_from_date()
    file_path = processing_log_file_for(month_key)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {
        "Log ID": str(uuid.uuid4())[:8],
        "Tenant ID": client,
        "Original File": original_file_name,
        "Processed File": os.path.basename(processed_file_path),
        "File Path": processed_file_path,
        "Date Processed": now,
        "Status": status,
    }
    append_row_to_csv(file_path, entry)

def load_processing_logs_for_month(month_key: str) -> List[Dict[str, Any]]:
    return load_csv_as_records(processing_log_file_for(month_key))

# ------------------------
# CDR request logs
# ------------------------
def add_cdr_request(tenant_id: str, email: str, date_from: date, date_to: date, reason: str):
    month_key = month_key_from_date()
    file_path = cdr_log_file_for(month_key)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {
        "Request ID": str(uuid.uuid4())[:8],
        "Tenant ID": tenant_id,
        "Email": email,
        "Date From": str(date_from),
        "Date To": str(date_to),
        "Reason": reason,
        "Date Submitted": now,
        "Status": "Pending",
    }
    append_row_to_csv(file_path, entry)

def load_cdr_requests_for_month(month_key: str) -> List[Dict[str, Any]]:
    return load_csv_as_records(cdr_log_file_for(month_key))

def update_cdr_request_status(month_key: str, request_id: str, new_status: str) -> bool:
    file_path = cdr_log_file_for(month_key)
    if not os.path.exists(file_path):
        return False
    records = load_csv_as_records(file_path)
    updated = False
    for r in records:
        if str(r.get("Request ID")) == str(request_id):
            r["Status"] = new_status
            updated = True
            r["Date Updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if updated:
        write_records_to_csv(file_path, records)
    return updated

# ------------------------
# Constants / UI choices
# ------------------------
CALL_TYPES = [
    "outbound call",
    "predictive_dial",
    "incoming call",
    "play_sound",
    "read_dtmf",
    "answering machine",
]
RATE_TYPES = ["per_minute", "per_second"]

# ------------------------
# Page Navigation
# ------------------------
page = st.sidebar.radio("📂 Navigation", ["Calculator", "Request CDR", "Manual", "Admin Dashboard"])

# ------------------------
# Calculator Page
# ------------------------
if page == "Calculator":
    st.info(
        "⚠️ **Disclaimer**: This call charge calculator is used to give an estimate of your call charge usage. "
        "The results provided are **not final**, and **international calls** may increase the estimated number."
    )
    st.title("📞 Call Charge Calculator (Dashboard)")

    # Upload CSV
    uploaded_file = st.file_uploader("Upload Dashboard CSV (exported from MiiTel Analytics)", type=["csv"])

    # Form inputs
    st.subheader("Client Configuration")
    client = st.text_input("Client ID (required)")
    rate = st.number_input("Default Rate (required)", min_value=0.0, value=720.0, format="%.2f")
    rate_type = st.selectbox("Rate Type", RATE_TYPES)
    chargeable_call_types = st.multiselect("Chargeable Call Types", CALL_TYPES, default=["outbound call", "predictive_dial"])

    st.subheader("Optional / Special Numbers (enter one per row)")
    number1 = st.text_input("Special Number 1 (optional)")
    number1_rate = st.number_input("Number 1 Rate", min_value=0.0, value=0.0, format="%.2f")
    number1_rate_type = st.selectbox("Number 1 Rate Type", RATE_TYPES, index=0)
    number1_chargeable = st.multiselect("Number 1 Chargeable Call Types", CALL_TYPES)

    number2 = st.text_input("Special Number 2 (optional)")
    number2_rate = st.number_input("Number 2 Rate", min_value=0.0, value=0.0, format="%.2f")
    number2_rate_type = st.selectbox("Number 2 Rate Type (Number 2)", RATE_TYPES, index=0)
    number2_chargeable = st.multiselect("Number 2 Chargeable Call Types (Number 2)", CALL_TYPES, key="n2cts")

    s2c = st.text_input("S2C Number (optional)")
    s2c_rate = st.number_input("S2C Rate", min_value=0.0, value=0.0, format="%.2f")
    s2c_rate_type = st.selectbox("S2C Rate Type", RATE_TYPES, index=0)

    # Process button with spinner to show loading and reduce double clicks
    if uploaded_file is not None and client.strip():
        if st.button("Process File"):
            with st.spinner("Processing dashboard CSV... this may take a moment. Please wait."):
                # write uploaded file to a temp file for processing
                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_input:
                    tmp_input.write(uploaded_file.read())
                    tmp_input.flush()

                try:
                    config = Files(
                        client=client.strip(),
                        dashboard=tmp_input.name,
                        output="output.csv",
                        carrier="Indosat",  # default to Indosat per your request
                        number1=number1 if number1 else None,
                        number1_rate=number1_rate,
                        number1_rate_type=number1_rate_type,
                        number1_chargeable_call_types=number1_chargeable,
                        number2=number2 if number2 else None,
                        number2_rate=number2_rate,
                        number2_rate_type=number2_rate_type,
                        number2_chargeable_call_types=number2_chargeable,
                        rate=rate,
                        rate_type=rate_type,
                        s2c=s2c if s2c else None,
                        s2c_rate=s2c_rate,
                        s2c_rate_type=s2c_rate_type,
                        chargeable_call_types=chargeable_call_types,
                    )

                    # process and save
                    call_details = process_dashboard_csv(config)
                    processed_fname = f"{client}_processed_{uuid.uuid4().hex[:6]}.csv"
                    processed_file_path = os.path.join(PROCESSED_DIR, processed_fname)
                    save_merged_csv(call_details, processed_file_path)

                    # add processing log (persistent)
                    add_processing_log(client.strip(), getattr(uploaded_file, "name", processed_fname), processed_file_path)

                    # provide download
                    with open(processed_file_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Download Processed CSV",
                            data=f,
                            file_name=f"{client}_processed.csv",
                            mime="text/csv",
                        )

                    st.success("Processing complete. File is available for download and stored for admin review.")
                except Exception as e:
                    st.error(f"Processing failed: {e}")
                finally:
                    try:
                        os.unlink(tmp_input.name)
                    except Exception:
                        pass

    else:
        st.info("Please upload a dashboard CSV and enter Client ID to enable processing.")

    if st.button("🔄 Reset Form"):
        # clears form state keys that matter
        for k in ["client", "rate", "rate_type", "chargeable_call_types",
                  "number1", "number1_rate", "number1_chargeable",
                  "number2", "number2_rate", "number2_chargeable",
                  "s2c", "s2c_rate", "uploaded_file"]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()

# ------------------------
# Request CDR Page
# ------------------------
elif page == "Request CDR":
    st.title("📨 Request CDR")
    st.info("Use this form to request an official CDR calculation (MiiTel FA team).")

    with st.form("cdr_form"):
        tenant_id = st.text_input("Tenant ID (required)")
        requester_name = st.text_input("Requester Name (optional)")
        email = st.text_input("Contact Email (required)")
        date_from = st.date_input("Date From", value=date.today())
        date_to = st.date_input("Date To", value=date.today())
        reason = st.text_area("Reason / Notes (optional)")

        submitted = st.form_submit_button("Submit Request")
        if submitted:
            if not tenant_id or not email:
                st.error("Tenant ID and Contact Email are required.")
            else:
                add_cdr_request(tenant_id.strip(), email.strip(), date_from, date_to, reason.strip())
                st.success("✅ Your CDR request has been submitted. Admin will review it.")

# ------------------------
# Admin Dashboard Page
# ------------------------
elif page == "Admin Dashboard":
    st.subheader("🛡️ Admin Dashboard")
    admin_pass = st.text_input("Enter admin password", type="password")
    if admin_pass != "supersecret":  # NOTE: replace with secure secret in production
        st.warning("Invalid or missing admin password.")
    else:
        # admin area
        st.markdown("### Select month")
        # collect months from both logs and cdr dirs
        months_set = set()
        for fname in os.listdir(LOGS_DIR):
            if fname.startswith("processing_logs_") and fname.endswith(".csv"):
                months_set.add(fname.replace("processing_logs_", "").replace(".csv", ""))
        for fname in os.listdir(CDR_DIR):
            if fname.startswith("cdr_requests_") and fname.endswith(".csv"):
                months_set.add(fname.replace("cdr_requests_", "").replace(".csv", ""))
        months = sorted(months_set)
        if not months:
            st.info("No historical months found yet.")
        else:
            default_index = len(months) - 1
            selected_month = st.selectbox("Month (YYYY_MM)", months, index=default_index)

            st.markdown("---")
            tab = st.radio("Admin Section", ["Processing Logs", "CDR Requests"])

            if tab == "Processing Logs":
                log_file = processing_log_file_for(selected_month)
                if os.path.exists(log_file):
                    df_logs = pd.read_csv(log_file)
                    st.dataframe(df_logs, use_container_width=True)
                    st.download_button("⬇️ Download Logs as CSV", df_logs.to_csv(index=False), f"processing_logs_{selected_month}.csv", "text/csv")
                    st.markdown("### Processed Files")
                    for idx, row in df_logs.iterrows():
                        path = row.get("File Path", "")
                        proc_file = row.get("Processed File", "")
                        if path and os.path.exists(path):
                            with open(path, "rb") as f:
                                st.download_button(label=f"⬇️ {proc_file}", data=f, file_name=proc_file, mime="text/csv", key=f"dl_proc_{idx}")
                        else:
                            st.text(f"⚠️ Missing file: {proc_file}")
                else:
                    st.info("No processing logs for selected month.")

            elif tab == "CDR Requests":
                cdr_file = cdr_log_file_for(selected_month)
                if os.path.exists(cdr_file):
                    df_cdr = pd.read_csv(cdr_file)
                    st.dataframe(df_cdr, use_container_width=True)
                    st.download_button("⬇️ Download CDR Requests (CSV)", df_cdr.to_csv(index=False), f"cdr_requests_{selected_month}.csv", "text/csv")

                    st.markdown("#### Update request status")
                    # allow admin to update statuses row by row
                    for i, rec in df_cdr.iterrows():
                        req_id = rec.get("Request ID")
                        tenant = rec.get("Tenant ID")
                        current_status = rec.get("Status", "Pending")
                        cols = st.columns([2, 2, 2, 2])
                        cols[0].write(f"**{req_id}** — {tenant}")
                        new_status = cols[1].selectbox("New status", ["Pending", "In Progress", "Completed", "Rejected"], index=["Pending", "In Progress", "Completed", "Rejected"].index(current_status) if current_status in ["Pending","In Progress","Completed","Rejected"] else 0, key=f"status_{req_id}")
                        if cols[2].button("Update", key=f"update_{req_id}"):
                            updated = update_cdr_request_status(selected_month, req_id, new_status)
                            if updated:
                                st.success(f"Request {req_id} updated to '{new_status}'.")
                                # re-run so table refreshes
                                st.rerun()
                            else:
                                st.error("Failed to update request (file may not exist).")
                        cols[3].write("")  # spacer
                else:
                    st.info("No CDR requests for selected month.")

# ------------------------
# Manual Page
# ------------------------
elif page == "Manual":
    st.title("📖 How to Use the Call Charge Calculator")

    steps = [
        "Step 1: Download the **call history CSV** from the **MiiTel Analytics Dashboard**.",
        "Step 2: Upload the CSV file into the calculator.",
        "Step 3: Enter the **client information** and **call charge settings**.",
        "Step 4: ⚠️ If **one number has different rates** for different call types, input the number separately for each rate and adjust the chargeable call types accordingly.",
        "Step 5: Set the **default rate correctly**.",
        "Step 6: For charged incoming calls, include all types from **incoming call** to **answering machine** as chargeable call types.",
        "Step 7: If there are no special numbers or settings, simply use the default rate.",
        "Step 8: In the processed CSV, you will find:\n   - **Round-up duration (minutes)**: for per-minute users (rounded per call).\n   - **Round-up duration (seconds)**: for per-second users (total duration in seconds).",
        "Step 9: ⚠️ For international calls, this calculator only gives **an estimate**. The official calculation can be requested from the **MiiTel FA team** via the **Request CDR form**.",
    ]

    for step in steps:
        st.markdown(f"- {step}")
