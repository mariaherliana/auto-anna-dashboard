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
def log_calculation(client: str, original_file: str, processed_file: str, file_path: str, status="Processed"):
    try:
        data = {
            "client": client,
            "original_file": original_file,
            "processed_file": processed_file,
            "file_path": file_path,
            "date_processed": datetime.now(),
            "status": status
        }
        supabase.table("calculator_logs").insert(data).execute()
        logging.info(f"Logged calculation for {client}: {data}")
    except Exception as e:
        logging.error(f"Failed to log calculation for {client}: {e}")

def log_cdr_request(tenant_id: str, email: str, date_from: date, date_to: date, reason: str, status="Pending"):
    try:
        data = {
            "tenant_id": tenant_id,
            "email": email,
            "date_from": date_from,
            "date_to": date_to,
            "reason": reason,
            "date_submitted": datetime.now(),
            "status": status
        }
        supabase.table("cdr_requests").insert(data).execute()
        logging.info(f"Logged CDR request for tenant {tenant_id}: {data}")
    except Exception as e:
        logging.error(f"Failed to log CDR request for tenant {tenant_id}: {e}")

# ------------------------
# Admin Utilities
# ------------------------
def fetch_calculator_logs(month: int = None) -> List[Dict[str, Any]]:
    logs = supabase.table("calculator_logs").select("*").execute().data
    if month:
        logs = [log for log in logs if datetime.fromisoformat(log["date_processed"]).month == month]
    return logs

def fetch_cdr_requests(month: int = None) -> List[Dict[str, Any]]:
    requests = supabase.table("cdr_requests").select("*").execute().data
    if month:
        requests = [req for req in requests if datetime.fromisoformat(req["date_submitted"]).month == month]
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
# Calculator Page
# ------------------------
if page == "Calculator":
    st.title("📞 Call Charge Calculator")
    uploaded_file = st.file_uploader("Upload Dashboard CSV", type=["csv"])
    client = st.text_input("Client ID (required)")
    rate = st.number_input("Default Rate", min_value=0.0, value=720.0)
    rate_type = st.selectbox("Rate Type", RATE_TYPES)
    chargeable_call_types = st.multiselect("Chargeable Call Types", CALL_TYPES, default=["outbound call","predictive_dial"])

    if uploaded_file and client.strip():
        if st.button("Process File"):
            with st.spinner("Processing..."):
                # Save uploaded file to temp
                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_input:
                    tmp_input.write(uploaded_file.read())
                    tmp_input.flush()
                try:
                    config = Files(
                        client=client.strip(),
                        dashboard=tmp_input.name,
                        output="output.csv",
                        carrier="Indosat",
                        chargeable_call_types=chargeable_call_types,
                        rate=rate,
                        rate_type=rate_type
                    )
                    call_details = process_dashboard_csv(config)
                    processed_fname = f"{client}_processed_{uuid.uuid4().hex[:6]}.csv"
                    processed_file_path = os.path.join(PROCESSED_DIR, processed_fname)
                    save_merged_csv(call_details, processed_file_path)

                    # Log calculation
                    log_calculation(client, getattr(uploaded_file, "name", processed_fname), processed_fname, processed_file_path)

                    # Provide download
                    with open(processed_file_path, "rb") as f:
                        st.download_button("⬇️ Download Processed CSV", f, f"{client}_processed.csv", "text/csv")
                    st.success("Processing complete and logged.")
                finally:
                    try:
                        os.unlink(tmp_input.name)
                    except Exception:
                        pass
    else:
        st.info("Please upload a CSV and enter Client ID.")

# ------------------------
# Request CDR Page
# ------------------------
elif page == "Request CDR":
    st.title("📨 Request CDR")
    with st.form("cdr_form"):
        tenant_id = st.text_input("Tenant ID (required)")
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
                st.success("✅ CDR request submitted.")

# ------------------------
# Admin Dashboard Page
# ------------------------
elif page == "Admin Dashboard":
    st.subheader("🛡️ Admin Dashboard")
    admin_pass = st.text_input("Admin Password", type="password")
    if admin_pass != "superadmin":
        st.warning("Invalid password.")
    else:
        month = st.selectbox("Filter Month", list(range(1,13)), index=datetime.now().month-1)
        tab = st.radio("Admin Section", ["Processing Logs", "CDR Requests"])

        if tab == "Processing Logs":
            logs = fetch_calculator_logs(month)
            df_logs = pd.DataFrame(logs)
            st.dataframe(df_logs)
            st.download_button("⬇️ Download Logs CSV", df_logs.to_csv(index=False), f"calculator_logs_{month}.csv", "text/csv")
            # Allow download of processed files
            for idx, row in df_logs.iterrows():
                path = row.get("file_path")
                fname = row.get("processed_file")
                if path and os.path.exists(path):
                    with open(path, "rb") as f:
                        st.download_button(f"⬇️ {fname}", f, fname, "text/csv", key=f"proc_{idx}")

        elif tab == "CDR Requests":
            requests = fetch_cdr_requests(month)
            df_req = pd.DataFrame(requests)
            st.dataframe(df_req)
            st.download_button("⬇️ Download CDR Requests CSV", df_req.to_csv(index=False), f"cdr_requests_{month}.csv", "text/csv")
            st.markdown("#### Update Request Status")
            for i, rec in df_req.iterrows():
                req_id = rec.get("request_id")
                current_status = rec.get("status","Pending")
                new_status = st.selectbox(f"Status for {req_id}", ["Pending","In Progress","Completed","Rejected"], index=["Pending","In Progress","Completed","Rejected"].index(current_status) if current_status in ["Pending","In Progress","Completed","Rejected"] else 0, key=f"status_{req_id}")
                if st.button(f"Update {req_id}", key=f"upd_{req_id}"):
                    update_cdr_status(req_id, new_status)
                    st.success(f"Updated {req_id} to {new_status}")
                    st.experimental_rerun()

# ------------------------
# Manual Page
# ------------------------
elif page == "Manual":
    st.title("📖 How to Use the Call Charge Calculator")
    steps = [
        "Step 1: Download CSV from MiiTel Analytics.",
        "Step 2: Upload CSV into the calculator.",
        "Step 3: Enter client info and rates.",
        "Step 4: Configure special numbers if any.",
        "Step 5: Submit to process file.",
        "Step 6: Download processed CSV.",
    ]
    for s in steps:
        st.markdown(f"- {s}")
