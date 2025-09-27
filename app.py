import streamlit as st
import pandas as pd
import tempfile
import os
import uuid
from datetime import datetime
from src.csv_processing import process_dashboard_csv, save_merged_csv
from src.FileConfig import Files

# ------------------------
# Page Setup
# ------------------------
st.set_page_config(
    page_title="MiiTel CC Calculator",  # 👈 Tab title
    page_icon="📞",                      # 👈 Emoji/Favicon
    layout="wide",                       # 👈 Wide layout
)

# ------------------------
# Setup
# ------------------------
PROCESSED_DIR = "processed_files"
os.makedirs(PROCESSED_DIR, exist_ok=True)

# ------------------------
# Reset function
# ------------------------
def reset_form():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ------------------------
# Initialize logs in session
# ------------------------
if "logs" not in st.session_state:
    st.session_state["logs"] = []

def add_log(client, file_name, file_path, status="Processed"):
    log_id = str(uuid.uuid4())[:8]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        "Log ID": log_id,
        "Tenant ID": client,
        "File Name": file_name,
        "File Path": file_path,
        "Date Processed": now,
        "Status": status,
    }
    st.session_state["logs"].append(log_entry)

# ------------------------
# Constants
# ------------------------
call_types = [
    "outbound call",
    "predictive_dial",
    "incoming call",
    "play_sound",
    "read_dtmf",
    "answering machine",
]
rate_types = ["per_minute", "per_second"]

# ------------------------
# Page Navigation
# ------------------------
page = st.sidebar.radio("📂 Navigation", ["Calculator", "Manual", "Admin Dashboard"])

# ------------------------
# Calculator Page
# ------------------------
if page == "Calculator":
    st.info(
        "⚠️ **Disclaimer**: This call charge calculator is used to give an estimate of your call charge usage. "
        "The results provided are **not final**, and **international calls** may increase the estimated number."
    )

    st.title("📞 Call Charge Calculator (Dashboard)")

    uploaded_file = st.file_uploader("Upload Dashboard CSV", type=["csv"], key="uploaded_file")

    st.subheader("Client Configuration")
    client = st.text_input("Client ID (required)", key="client")
    rate = st.number_input("Rate (required)", min_value=0.0, value=720.0, key="rate")
    rate_type = st.selectbox("Rate Type", rate_types, index=0, key="rate_type")
    chargeable_call_types = st.multiselect(
        "Chargeable Call Types",
        call_types,
        default=["outbound call", "predictive_dial"],
        key="chargeable_call_types"
    )

    st.subheader("Optional Settings")
    # Number 1
    number1 = st.text_input("Special Number 1 (optional)", key="number1")
    number1_rate = st.number_input("Number 1 Rate", min_value=0.0, value=0.0, key="number1_rate")
    number1_rate_type = st.selectbox("Number 1 Rate Type", rate_types, index=0, key="number1_rate_type")
    number1_chargeable = st.multiselect(
        "Number 1 Chargeable Call Types",
        call_types,
        key="number1_chargeable"
    )

    # Number 2
    number2 = st.text_input("Special Number 2 (optional)", key="number2")
    number2_rate = st.number_input("Number 2 Rate", min_value=0.0, value=0.0, key="number2_rate")
    number2_rate_type = st.selectbox("Number 2 Rate Type", rate_types, index=0, key="number2_rate_type")
    number2_chargeable = st.multiselect(
        "Number 2 Chargeable Call Types",
        call_types,
        key="number2_chargeable"
    )

    # S2C
    s2c = st.text_input("S2C Number (optional)", key="s2c")
    s2c_rate = st.number_input("S2C Rate", min_value=0.0, value=0.0, key="s2c_rate")
    s2c_rate_type = st.selectbox("S2C Rate Type", rate_types, index=0, key="s2c_rate_type")

    if uploaded_file and client:
        if st.button("Process File"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_input:
                tmp_input.write(uploaded_file.read())
                tmp_input.flush()

                config = Files(
                    client=client,
                    dashboard=tmp_input.name,
                    output="output.csv",
                    carrier="Indosat",  # always use Indosat
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

                processed_file_path = os.path.join(
                    PROCESSED_DIR, f"{client}_processed_{uuid.uuid4().hex[:6]}.csv"
                )
                save_merged_csv(call_details, processed_file_path)

                with open(processed_file_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Download Processed CSV",
                        data=f,
                        file_name=f"{client}_processed.csv",
                        mime="text/csv"
                    )

                add_log(client, uploaded_file.name, processed_file_path)
                os.unlink(tmp_input.name)

    if st.button("🔄 Reset Form"):
        reset_form()

# ------------------------
# Admin Dashboard Page
# ------------------------
elif page == "Admin Dashboard":
    st.subheader("🛡️ Admin Dashboard")

    admin_pass = st.text_input("Enter admin password", type="password")
    if admin_pass == "supersecret":  # 🔒 Replace with env variable in production
        if st.session_state["logs"]:
            df_logs = pd.DataFrame(st.session_state["logs"])
            st.dataframe(df_logs, use_container_width=True)

            st.download_button(
                "⬇️ Download Logs as CSV",
                df_logs.to_csv(index=False),
                "processing_logs.csv",
                "text/csv"
            )

            st.markdown("### 📂 Processed Files")
            for log in st.session_state["logs"]:
                if "File Path" in log and os.path.exists(log["File Path"]):
                    with open(log["File Path"], "rb") as f:
                        st.download_button(
                            label=f"⬇️ Download {log['File Name']}",
                            data=f,
                            file_name=log["File Name"],
                            mime="text/csv",
                            key=f"dl_{log['Log ID']}"
                        )
                else:
                    st.text(f"⚠️ File for {log['File Name']} not found.")
        else:
            st.info("No logs yet. Process a file to see history.")
    else:
        st.warning("Invalid or missing admin password.")

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
        "Step 8: In the processed CSV, you will find: - **Round-up duration (minutes)**: for per-minute users (rounded per call). - **Round-up duration (seconds)**: for per-second users (total duration in seconds).",
        "Step 9: ⚠️ For international calls, this calculator only gives **an estimate**. The official calculation can be requested from the **MiiTel FA team** via the **Request CDR form**.",
    ]



    for step in steps:
        st.markdown(f"- {step}")
