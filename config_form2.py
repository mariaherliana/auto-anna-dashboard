import streamlit as st
import re
from config import CONFIG
import shutil
import datetime
import os
import json

CONFIG_PY_PATH = "config.py"

st.title("🔧 Add Config (Client Name Only)")

selectbox_defaults = {
    "rate_type": "per_minute",
    "s2c_rate_type": "per_minute",
    "number1_rate_type": "per_minute",
    "number2_rate_type": "per_minute"
}

valid_carriers = ["Atlasat", "Indosat", "Telkom", "Quiros", "MGM"]

# Ensure a valid default is set
if "carrier" not in st.session_state or st.session_state["carrier"] not in valid_carriers:
    st.session_state["carrier"] = "Atlasat"

available_call_types = [
    "outbound call",
    "predictive dialer",
    "incoming call",
    "play_sound",
    "read_dtmf",
    "answering machine",
]

for key, default in selectbox_defaults.items():
    if key not in st.session_state or st.session_state[key] not in ["per_minute", "per_second"]:
        st.session_state[key] = default

def generate_config_entry(data: dict) -> str:
    def quote(value):
        if isinstance(value, str):
            return f'"{value}"'
        return str(value)

    return f"""    Files(
        client={quote(data["client"])},
        dashboard={quote(data["dashboard"])},
        output={quote(data["output"])},
        carrier={quote(data["carrier"])},
        number1={quote(data["number1"]) if data["number1"] else "None"},
        number1_rate={data["number1_rate"]},
        number1_rate_type={quote(data["number1_rate_type"])},
        number1_chargeable_call_types={data["number1_chargeable_call_types"]},
        number2={quote(data["number2"]) if data["number2"] else "None"},
        number2_rate={data["number2_rate"]},
        number2_rate_type={quote(data["number2_rate_type"])},
        number2_chargeable_call_types={data["number1_chargeable_call_types"]},
        rate={data["rate"]},
        rate_type={quote(data["rate_type"])},
        s2c={quote(data["s2c"]) if data["s2c"] else "None"},
        s2c_rate={data["s2c_rate"]},
        s2c_rate_type={quote(data["s2c_rate_type"])},
        chargeable_call_types={json.dumps(data["chargeable_call_types"])},
    ),"""

def insert_entry_to_config(new_entry: str, client: str, config_path: str = "config.py"):
    with open(config_path, "r") as f:
        config_lines = f.readlines()

    start_index = None
    end_index = None
    inside_files_block = False

    for i, line in enumerate(config_lines):
        if f'client="{client}"' in line or f"client='{client}'" in line:
            inside_files_block = True
            start_index = i
        elif inside_files_block and line.strip().endswith("),"):
            end_index = i
            break

    if start_index is not None and end_index is not None:
        # Remove the old entry for the client
        del config_lines[start_index:end_index + 1]

    # Find where CONFIG list starts (flexible)
    for j, line in enumerate(config_lines):
        stripped = line.strip()
        if stripped.startswith("CONFIG") and "=" in stripped and "[" in stripped:
            insert_pos = j + 1
            config_lines.insert(insert_pos, new_entry + "\n")
            break
    else:
        raise ValueError("CONFIG list definition not found in config.py")

    with open(config_path, "w") as f:
        f.writelines(config_lines)

form_keys = [
    "client_name", "carrier", "rate", "rate_type", "s2c",
    "s2c_rate", "s2c_rate_type", "chargeable_call_types",
    "number1", "number1_rate", "number1_rate_type", "number1_chargeable_call_types_str",
    "number2", "number2_rate", "number2_rate_type", "number2_chargeable_call_types_str"
]

# Initialize session state for all keys if not set
for key in form_keys + ["folder_prefix"]:
    if key not in st.session_state:
        st.session_state[key] = "" if key != "rate" and not key.endswith("_rate") else 0.0

def reset_form():
    keep_keys = ["folder_prefix", "chargeable_call_types"]
    reset_keys = [k for k in st.session_state.keys() if k not in keep_keys]

    for k in reset_keys:
        del st.session_state[k]

    st.rerun()

with st.form("client_only_config_form"):
    client_name = st.text_input("Client name (e.g., tenant-id)", key="client_name")
    folder_prefix = st.text_input("Folder prefix (e.g., 202505)", key="folder_prefix")

    # Show paths markdown only if client_name and folder_prefix are set
    if client_name and folder_prefix:
        dashboard_path = f"{folder_prefix}/DB/{client_name}.csv"
        output_path = f"{folder_prefix}/Processed/{client_name}.csv"

        st.session_state["md_dashboard"] = f"📁 **Dashboard path:** `{dashboard_path}`"
        st.session_state["md_output"] = f"📁 **Output path:** `{output_path}`"

    # Render markdown only if it exists in session state
    if "md_dashboard" in st.session_state:
        st.markdown(st.session_state["md_dashboard"])
    if "md_output" in st.session_state:
        st.markdown(st.session_state["md_output"])

    carrier = st.selectbox("Carrier", valid_carriers, key="carrier")
    rate = st.number_input("Rate", value=720.0, min_value=0.0, step=0.1, format="%.2f", key="rate")
    rate_type = st.selectbox("Rate Type", ["per_minute", "per_second"], key="rate_type")
    s2c = st.text_input("S2C number (optional)", key="s2c")
    s2c_rate = st.number_input("S2C Rate", value=0.0, min_value=0.0, step=0.1, format="%.2f", key="s2c_rate")
    s2c_rate_type = st.selectbox("S2C Rate Type", ["per_minute", "per_second"], key="s2c_rate_type")
    st.markdown("**Chargeable Call Types**")
    # Initialize an empty list to hold selected call types
    chargeable_call_types = []
    # Show each call type as a checkbox
    for call_type in available_call_types:
        if st.checkbox(call_type, key=f"charge_{call_type}"):
            chargeable_call_types.append(call_type)

    number1 = st.text_input("Number 1 (optional)", key="number1")
    number1_rate = st.number_input("Number 1 Rate", value=0.0, min_value=0.0, step=0.1, format="%.2f", key="number1_rate")
    number1_rate_type = st.selectbox("Number 1 Rate Type", ["per_minute", "per_second"], key="number1_rate_type")
    number1_chargeable_call_types_str = st.text_input("Number 1 Chargeable Call Types (comma separated)", "")
    number1_chargeable_call_types = [ct.strip() for ct in number1_chargeable_call_types_str.split(",") if ct.strip()]

    number2 = st.text_input("Number 2 (optional)", key="number2")
    number2_rate = st.number_input("Number 2 Rate", value=0.0, min_value=0.0, step=0.1, format="%.2f", key="number2_rate")
    number2_rate_type = st.selectbox("Number 2 Rate Type", ["per_minute", "per_second"], key="number2_rate_type")
    number2_chargeable_call_types_str = st.text_input("Number 2 Chargeable Call Types (comma separated)", "")
    number2_chargeable_call_types = [ct.strip() for ct in number2_chargeable_call_types_str.split(",") if ct.strip()]

    existing_clients = [c.client for c in CONFIG]
    should_overwrite = False

    if client_name in existing_clients:
        overwrite_choice = st.radio(f"⚠ Client `{client_name}` already exists. Overwrite?", ["No", "Yes"], index=0)
        should_overwrite = overwrite_choice == "Yes"

    submitted = st.form_submit_button("➕ Add to Config")

    if submitted:
        if not client_name or not folder_prefix:
            st.error("Please fill in both client name and folder prefix.")
        elif client_name in existing_clients and not should_overwrite:
            st.warning("❌ Entry not added. Choose 'Yes' to overwrite.")
        else:
            data = {
                "client": client_name,
                "dashboard": dashboard_path,
                "output": output_path,
                "carrier": carrier,
                "number1": number1 or None,
                "number1_rate": number1_rate,
                "number1_rate_type": number1_rate_type,
                "number1_chargeable_call_types": number1_chargeable_call_types,
                "number2": number2 or None,
                "number2_rate": number2_rate,
                "number2_rate_type": number2_rate_type,
                "number2_chargeable_call_types": number2_chargeable_call_types,
                "rate": rate,
                "rate_type": rate_type,
                "s2c": s2c or None,
                "s2c_rate": s2c_rate,
                "s2c_rate_type": s2c_rate_type,
                "chargeable_call_types": chargeable_call_types,
            }

            new_entry = generate_config_entry(data)
            insert_entry_to_config(new_entry, client_name)

            st.success("✔ Config added or updated successfully!")
            st.code(f"""
Dashboard: {dashboard_path}
Output:    {output_path}
""", language="text")

# Outside form
if st.button("🔄 Reset Form"):
    reset_form()
