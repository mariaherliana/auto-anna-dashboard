import streamlit as st
import pandas as pd
from src.csv_processing import process_dashboard_csv, save_merged_csv
from src.FileConfig import Files
import tempfile
import os

st.title("Auto-Anna (Dashboard Only)")

# Reset function
def reset_form():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# Constants
carriers = ["Atlasat", "Indosat", "Telkom", "Quiros", "MGM"]
call_types = [
    "outbound call",
    "predictive dialer",
    "incoming call",
    "play_sound",
    "read_dtmf",
    "answering machine",
]
rate_types = ["per_minute", "per_second"]

# Upload CSV
uploaded_file = st.file_uploader("Upload Dashboard CSV", type=["csv"], key="uploaded_file")

# Form inputs
st.subheader("Client Configuration")
client = st.text_input("Client ID (required)", key="client")
carrier = st.selectbox("Carrier (required)", carriers, index=0, key="carrier")
rate = st.number_input("Rate (required)", min_value=0.0, value=720.0, key="rate")
rate_type = st.selectbox("Rate Type", rate_types, index=0, key="rate_type")
chargeable_call_types = st.multiselect(
    "Chargeable Call Types",
    call_types,
    default=["outbound call", "predictive dialer"],
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

# Process button
if uploaded_file and client and carrier:
    if st.button("Process File"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_input:
            tmp_input.write(uploaded_file.read())
            tmp_input.flush()

            config = Files(
                client=client,
                dashboard=tmp_input.name,
                output="output.csv",
                carrier=carrier,
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

            call_details = process_dashboard_csv(config.dashboard, config.carrier, client=config.client)

            tmp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
            save_merged_csv(call_details, tmp_output.name)

            with open(tmp_output.name, "rb") as f:
                st.download_button(
                    label="Download Processed CSV",
                    data=f,
                    file_name=f"{client}_processed.csv",
                    mime="text/csv"
                )

            os.unlink(tmp_input.name)
            os.unlink(tmp_output.name)

# Reset button
if st.button("🔄 Reset Form"):
    reset_form()
