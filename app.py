import streamlit as st
import pandas as pd
import tempfile
import os
import uuid
from datetime import datetime, date
from typing import List, Dict, Any
from src.csv_processing import process_dashboard_csv, save_merged_csv
from src.FileConfig import Files
import logging
from supabase import create_client, Client
import requests

# ------------------------
# Page Setup
# ------------------------
st.set_page_config(
    page_title="MiiTel CC Calculator",
    page_icon="📞",
    layout="wide",
)

# ------------------------
# Supabase Setup
# ------------------------
SUPABASE_URL = st.secrets["SUPABASE"]["url"]
SUPABASE_KEY = st.secrets["SUPABASE"]["key"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ------------------------
# Directories (local cache for processed files)
# ------------------------
PROCESSED_DIR = "processed_files"
os.makedirs(PROCESSED_DIR, exist_ok=True)

# ------------------------
# Backend logging
# ------------------------
BACKEND_LOG_FILE = os.path.join(PROCESSED_DIR, "backend_activity.log")
logging.basicConfig(
    filename=BACKEND_LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ------------------------
# Logging Functions (Supabase)
# ------------------------
def log_calculation(client: str, original_file: str, processed_file: str, local_file_path: str, status="Processed"):
    try:
        bucket_name = "calculator_results"
        file_key = f"{client}/{processed_file}"

        # Upload file
        with open(local_file_path, "rb") as f:
            result = supabase.storage.from_(bucket_name).upload(file_key, f, overwrite=True)
        if result.get("error"):
            logging.error(f"Supabase upload failed: {result['error']}")
            return

        file_url = supabase.storage.from_(bucket_name).get_public_url(file_key).url
        if not file_url:
            logging.error(f"Failed to get file URL for {file_key}")
            return

        data = {
            "client": client,
            "original_file": original_file,
            "processed_file": processed_file,
            "file_url": file_url,
            "date_processed": datetime.now().isoformat(),
            "status": status
        }

        resp = supabase.table("calculator_logs").insert([data]).execute()
        if getattr(resp, "error", None):
            logging.error(f"Supabase insert failed: {resp.error}")
        else:
            logging.info(f"Logged calculation for {client}: {data}")

    except Exception as e:
        logging.error(f"Failed to log calculation for {client}: {e}")

def log_cdr_request(tenant_id: str, email: str, date_from: date, date_to: date, reason: str, status="Pending"):
    try:
        data = {
            "tenant_id": tenant_id,
            "email": email,
            "date_from": date_from.isoformat() if isinstance(date_from, date) else date_from,
            "date_to": date_to.isoformat() if isinstance(date_to, date) else date_to,
            "reason": reason,
            "date_submitted": datetime.now().isoformat(),
            "status": status
        }
        response = supabase.table("cdr_requests").insert([data]).execute()
        if getattr(response, "error", None):
            logging.error(f"Supabase insert failed: {response.error}")
        else:
            logging.info(f"Logged CDR request for tenant {tenant_id}")

# ------------------------
# Admin Utilities
# ------------------------
def parse_supabase_timestamp(ts: str) -> datetime:
    """
    Converts Supabase TIMESTAMP string to datetime object, stripping trailing Z or fractional seconds if needed.
    """
    ts_clean = ts.split('.')[0]  # remove fractional seconds
    ts_clean = ts_clean.replace('Z','')  # remove trailing Z if UTC
    return datetime.fromisoformat(ts_clean)

def fetch_calculator_logs(month: int = None) -> List[Dict[str, Any]]:
    logs = supabase.table("calculator_logs").select("*").execute().data
    if month:
        filtered = []
        for log in logs:
            dt = parse_supabase_timestamp(log["date_processed"])
            if dt.month == month:
                filtered.append(log)
        logs = filtered
    return logs

def fetch_cdr_requests(month: int = None) -> List[Dict[str, Any]]:
    requests = supabase.table("cdr_requests").select("*").execute().data
    if month:
        filtered = []
        for req in requests:
            dt = parse_supabase_timestamp(req["date_submitted"])
            if dt.month == month:
                filtered.append(req)
        requests = filtered
    return requests

def update_cdr_status(request_id: int, new_status: str):
    supabase.table("cdr_requests").update({"status": new_status}).eq("request_id", request_id).execute()

# ------------------------
# Constants / UI choices
# ------------------------
CALL_TYPES = ["outbound call","predictive_dial","incoming call","play_sound","read_dtmf","answering machine"]
RATE_TYPES = ["per_minute","per_second"]

# ------------------------
# Page Navigation
# ------------------------
page = st.sidebar.radio("📂 Navigation", ["Calculator", "Request CDR", "Manual", "Admin Dashboard"])

# ------------------------
# Calculator Page (UNCHANGED FORM + CALCULATION)
# ------------------------
if page == "Calculator":
    # Everything from your original Calculator page goes here without any changes.
    # This includes all input fields, special numbers, S2C numbers, rate logic, and process button.
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

    if uploaded_file is not None and client.strip():
        if st.button("Process File"):
            with st.spinner("Processing dashboard CSV... this may take a moment. Please wait."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_input:
                    tmp_input.write(uploaded_file.read())
                    tmp_input.flush()
                try:
                    config = Files(
                        client=client.strip(),
                        dashboard=tmp_input.name,
                        output="output.csv",
                        carrier="Indosat",
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
                    call_details = process_dashboard_csv(config)
                    processed_fname = f"{client}_processed_{uuid.uuid4().hex[:6]}.csv"
                    processed_file_path = os.path.join(PROCESSED_DIR, processed_fname)
                    save_merged_csv(call_details, processed_file_path)

                    # Log calculation to Supabase
                    log_calculation(client.strip(), getattr(uploaded_file, "name", processed_fname), processed_fname, processed_file_path)

                    # Provide download
                    with open(processed_file_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Download Processed CSV",
                            data=f,
                            file_name=f"{client}_processed.csv",
                            mime="text/csv",
                        )
                    st.success("Processing complete. File is available for download and stored for admin review.")
                finally:
                    try:
                        os.unlink(tmp_input.name)
                    except Exception:
                        pass
    else:
        st.info("Please upload a dashboard CSV and enter Client ID to enable processing.")

    if st.button("🔄 Reset Form"):
        for k in ["client", "rate", "rate_type", "chargeable_call_types",
                  "number1", "number1_rate", "number1_chargeable",
                  "number2", "number2_rate", "number2_chargeable",
                  "s2c", "s2c_rate", "uploaded_file"]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()

# ------------------------
# Request CDR Page (unchanged, now logs to Supabase)
# ------------------------
elif page == "Request CDR":
    st.title("📨 Request CDR")
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
                log_cdr_request(tenant_id.strip(), email.strip(), date_from, date_to, reason.strip())
                st.success("✅ Your CDR request has been submitted. Admin will review it.")

# ------------------------
# Admin Dashboard Page
# ------------------------
elif page == "Admin Dashboard":
    st.subheader("🛡️ Admin Dashboard")
    admin_pass = st.text_input("Enter admin password", type="password")
    if admin_pass != "supersecret":
        st.warning("Invalid password.")
    else:
        # Select month filter (integer)
        month = st.selectbox("Select Month", list(range(1,13)), index=datetime.now().month-1)

        # Choose tab
        tab = st.radio("Admin Section", ["Processing Logs", "CDR Requests"])

        if tab == "Processing Logs":
            logs = fetch_calculator_logs(month)
            df_logs = pd.DataFrame(logs)
            st.dataframe(df_logs)
            st.download_button(
                "⬇️ Download Logs CSV",
                df_logs.to_csv(index=False),
                f"calculator_logs_{month}.csv",
                "text/csv"
            )
        
            st.markdown("#### Download Processed Files")
            for idx, row in df_logs.iterrows():
            fname = row.get("processed_file")
            file_url = row.get("file_url")
            if file_url:
                resp = requests.get(file_url)
                st.download_button(
                    label=f"⬇️ {fname}",
                    data=resp.content,
                    file_name=fname,
                    mime="text/csv"
                )

        elif tab == "CDR Requests":
            requests = fetch_cdr_requests(month)
            df_req = pd.DataFrame(requests)
            st.dataframe(df_req)
            st.download_button("⬇️ Download CDR Requests CSV", df_req.to_csv(index=False), f"cdr_requests_{month}.csv", "text/csv")

            st.markdown("#### Update Request Status")
            for i, rec in df_req.iterrows():
                req_id = rec.get("request_id")
                current_status = rec.get("status","Pending")
                new_status = st.selectbox(
                    f"Status for {req_id}",
                    ["Pending","In Progress","Completed","Rejected"],
                    index=["Pending","In Progress","Completed","Rejected"].index(current_status) if current_status in ["Pending","In Progress","Completed","Rejected"] else 0,
                    key=f"status_{req_id}"
                )
                if st.button(f"Update {req_id}", key=f"upd_{req_id}"):
                    update_cdr_status(req_id, new_status)
                    st.success(f"Updated {req_id} to {new_status}")
                    st.rerun()

# ------------------------
# Manual Page (unchanged)
# ------------------------
elif page == "Manual":
    st.title("📖 How to Use the Call Charge Calculator")
    steps = [
        "Step 1: Download the call history CSV from MiiTel Analytics Dashboard.",
        "Step 2: Upload the CSV file into the calculator.",
        "Step 3: Enter the client information and call charge settings.",
        "Step 4: Configure special numbers if needed.",
        "Step 5: Set the default rate correctly.",
        "Step 6: Submit to process file.",
        "Step 7: Download processed CSV.",
    ]
    for s in steps:
        st.markdown(f"- {s}")
