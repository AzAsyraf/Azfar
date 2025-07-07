import streamlit as st
import re
import os
import pandas as pd
from io import BytesIO

# --- CONFIG ---
st.set_page_config(page_title="GD&T Tolerance Extractor", layout="wide")
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

# --- LOGO SECTION ---
left_col, center_col, right_col = st.columns([1, 3, 1])
with left_col:
    st.image("download1.png", width=100)
with center_col:
    st.markdown(
        f"<h1 style='text-align: center; color: {'#FFFFFF' if st.session_state.dark_mode else '#003366'};'>"
        f"GD&T Tolerance Value Extractor</h1>",
        unsafe_allow_html=True,
    )
with right_col:
    st.image("images.png", width=100)

# --- THEME TOGGLE ---
theme_toggle = st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode)
st.session_state.dark_mode = theme_toggle
if theme_toggle:
    st.markdown(
        """
        <style>
        body { background-color: #2c2f33; color: #f0f0f0; }
        .stApp { background-color: #2c2f33; color: #f0f0f0; }
        </style>
        """, unsafe_allow_html=True
    )

# --- FILE UPLOAD ---
uploaded_file = st.file_uploader(
    "📤 Upload STEP / STP / TXT File", type=["step", "stp", "txt"])

# --- MAIN EXTRACTION FUNCTION ---


def extract_tolerance_values(text):
    lines = text.splitlines()
    line_dict = {
        re.match(r"(#\d+)\s*=", line).group(1): line.strip()
        for line in lines if re.match(r"(#\d+)\s*=", line)
    }

    tol_pattern = re.compile(
        r"(#\d+)\s*=\s*(CYLINDRICITY|FLATNESS|STRAIGHTNESS|ROUNDNESS)_TOLERANCE"
        r"\(\s*'[^']*'\s*,\s*''\s*,\s*(#\d+)", re.IGNORECASE
    )

    datum_pattern = re.compile(
        r"#\d+\s*=\s*DATUM_FEATURE\(\s*'[^']*?\((\w)\)'", re.IGNORECASE
    )

    tol_results = []
    datum_results = []

    for match in tol_pattern.finditer(text):
        _, tol_type, ref_id = match.groups()
        definition = line_dict.get(ref_id, "")
        value_match = re.search(
            r"(?:LENGTH_MEASURE|VALUE_REPRESENTATION_ITEM)\s*\(\s*([\d.]+)", definition
        )
        if value_match:
            value = value_match.group(1)
            value = f"±{value}"  # Add ± prefix
            label = "CIRCULARITY" if tol_type.upper() == "ROUNDNESS" else tol_type.upper()
            tol_results.append((label.capitalize(), value))

    for match in datum_pattern.finditer(text):
        datum_letter = match.group(1)
        datum_results.append(datum_letter)

    datum_results = sorted(set(datum_results))

    if not tol_results and not datum_results:
        return None

    data = tol_results + [("Datum", letter) for letter in datum_results]
    return pd.DataFrame(data, columns=["Type", "Value"])


# --- PROCESS FILE ---
if uploaded_file:
    file_text = uploaded_file.read().decode("utf-8", errors="ignore")
    st.success(f"📁 File loaded: {uploaded_file.name}")
    result_df = extract_tolerance_values(file_text)

    if result_df is not None:
        st.subheader("📄 Extracted Results")
        st.dataframe(result_df, use_container_width=True)

        col1, col2 = st.columns([1, 2])
        with col1:
            file_format = st.selectbox("📄 Save as", [".txt", ".csv", ".xlsx"])
        with col2:
            if st.button("💾 Download"):
                if file_format == ".txt":
                    output = "Type            Value\n" + "-"*25 + "\n"
                    for _, row in result_df.iterrows():
                        output += f"{row['Type']:<15} {row['Value']}\n"
                    st.download_button(
                        "📥 Download TXT", output, file_name="tolerance.txt")

                elif file_format == ".csv":
                    csv_data = result_df.to_csv(index=False)
                    st.download_button(
                        "📥 Download CSV", csv_data, file_name="tolerance.csv")

                elif file_format == ".xlsx":
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        result_df.to_excel(
                            writer, index=False, sheet_name="GD&T Tolerances")
                    st.download_button(
                        "📥 Download Excel", output.getvalue(), file_name="tolerance.xlsx")

    else:
        st.warning("⚠️ No tolerance or datum data found.")
else:
    st.info("📂 Upload a STEP, STP or TXT file to extract tolerance values.")
