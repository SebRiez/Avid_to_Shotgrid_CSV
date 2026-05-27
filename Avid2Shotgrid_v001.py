import streamlit as st
import pandas as pd
import io
import os
from datetime import datetime

def convert_dataframe(df_source, handle_mode_start, handle_mode_end, handle_mode_duration):
    df_target = pd.DataFrame()

    # Strip invisible characters from all column names
    df_source.columns = df_source.columns.astype(str).str.strip()

    # Safety check for required columns
    required_columns = ['Name', 'Frame Count Start', 'Frame Count End', 'handles', 'Frame Count Duration']
    missing_columns = [col for col in required_columns if col not in df_source.columns]

    if missing_columns:
        st.error(f"Critical error: Required columns not found: {missing_columns}")
        st.info(f"Columns found in the file: {list(df_source.columns[:10])}...")
        st.stop()

    # Clean contents and convert to numeric
    df_source['Name'] = df_source['Name'].astype(str).str.strip()
    df_source['Frame Count Start'] = pd.to_numeric(df_source['Frame Count Start'], errors='coerce')
    df_source['Frame Count End'] = pd.to_numeric(df_source['Frame Count End'], errors='coerce')
    df_source['handles'] = pd.to_numeric(df_source['handles'], errors='coerce').fillna(0)
    df_source['Frame Count Duration'] = pd.to_numeric(df_source['Frame Count Duration'], errors='coerce')

    # --- TRANSFORMATION LOGIC ---

    # 1. Source Name first 17 characters -> Target Link
    df_target['Link'] = df_source['Name'].str[:17]

    # 2. Source Name full -> Target File name
    df_target['File name'] = df_source['Name']

    # 3. EMPTY: Format File Type
    df_target['Format File Type'] = ""

    # 4. Flexible Start Frame (First frame Frame in)
    if handle_mode_start == "− Subtract":
        df_target['First frame Frame in'] = df_source['Frame Count Start'] - df_source['handles']
    elif handle_mode_start == "+ Add":
        df_target['First frame Frame in'] = df_source['Frame Count Start'] + df_source['handles']
    else:  # Ignore
        df_target['First frame Frame in'] = df_source['Frame Count Start']

    # 5. Flexible End Frame (Last frame Frame Out)
    if handle_mode_end == "+ Add":
        df_target['Last frame Frame Out'] = df_source['Frame Count End'] + df_source['handles']
    elif handle_mode_end == "− Subtract":
        df_target['Last frame Frame Out'] = df_source['Frame Count End'] - df_source['handles']
    else:  # Ignore
        df_target['Last frame Frame Out'] = df_source['Frame Count End']

    # 6. Flexible Duration Frame (Working duration Frame Count)
    if handle_mode_duration == "+ Add":
        df_target['Working duration Frame Count'] = df_source['Frame Count Duration'] + (2 * df_source['handles'])
    elif handle_mode_duration == "− Subtract":
        df_target['Working duration Frame Count'] = df_source['Frame Count Duration'] - (2 * df_source['handles'])
    else:  # Ignore
        df_target['Working duration Frame Count'] = df_source['Frame Count Duration']

    # 7. EMPTY: Description, Submitted For, Artist and Submission
    df_target['Description'] = ""
    df_target['Submitted For'] = ""
    df_target['Artist'] = ""
    df_target['Submission'] = ""

    # Format as integers (no decimal places)
    for col in ['First frame Frame in', 'Last frame Frame Out', 'Working duration Frame Count']:
        df_target[col] = df_target[col].fillna(0).astype(int)

    return df_target


# --- Streamlit UI ---
st.set_page_config(page_title="Avid TabDelimited to Shotgrid CSV", layout="wide")

st.title("🎬 Avid TabDelimited to Shotgrid CSV")
st.write("Converts the tab-delimited source file directly into the target format for ShotGrid.")

st.markdown("---")

# --- Settings with segmented_control ---
st.subheader("⚙️ Handle calculation options:")

col_start, col_end, col_dur = st.columns(3)

with col_start:
    st.caption("⏮ Frame Count Start (In-Frame)")
    handle_mode_start = st.segmented_control(
        "In-Frame",
        options=["− Subtract", "+ Add", "Ignore"],
        default="− Subtract",
        label_visibility="collapsed",
        key="handle_start",
    )

with col_end:
    st.caption("⏭ Frame Count End (Out-Frame)")
    handle_mode_end = st.segmented_control(
        "Out-Frame",
        options=["+ Add", "− Subtract", "Ignore"],
        default="+ Add",
        label_visibility="collapsed",
        key="handle_end",
    )

with col_dur:
    st.caption("⏱ Frame Count Duration")
    handle_mode_duration = st.segmented_control(
        "Duration",
        options=["+ Add", "− Subtract", "Ignore"],
        default="+ Add",
        label_visibility="collapsed",
        key="handle_duration",
    )

st.markdown("---")

# --- File upload area ---
uploaded_file = st.file_uploader("Upload tab-delimited source file (.txt)", type=["txt"])

if uploaded_file is not None:
    try:
        # Generate dynamic export filename
        base_filename = os.path.splitext(uploaded_file.name)[0]
        current_date = datetime.now().strftime("%y%m%d")
        export_filename = f"{base_filename}_toShotgrid_{current_date}_v01.csv"

        # Read file as raw bytes
        raw_bytes = uploaded_file.getvalue()

        # Improved encoding detection
        try:
            text_content = raw_bytes.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                text_content = raw_bytes.decode('utf-16')
            except UnicodeDecodeError:
                text_content = raw_bytes.decode('latin-1', errors='ignore')

        # Normalise line endings
        lines = [line for line in text_content.replace('\r\n', '\r').replace('\n', '\r').split('\r') if line.strip()]

        # Split each line by tab
        parsed_data = [line.split('\t') for line in lines]

        # Separate header and data rows
        header = [col.strip() for col in parsed_data[0]]
        data_rows = parsed_data[1:]

        # Align column count
        adjusted_rows = []
        for row in data_rows:
            if len(row) < len(header):
                row += [""] * (len(header) - len(row))
            elif len(row) > len(header):
                row = row[:len(header)]
            adjusted_rows.append(row)

        # Build DataFrame
        df_source = pd.DataFrame(adjusted_rows, columns=header)
        df_source.columns = df_source.columns.astype(str).str.strip()

        # Run conversion with user settings
        df_converted = convert_dataframe(df_source, handle_mode_start, handle_mode_end, handle_mode_duration)

        # Show preview
        st.subheader("Preview of converted KLR list:")
        st.dataframe(df_converted)

        # Prepare CSV in memory for download
        csv_buffer = io.StringIO()
        df_converted.to_csv(csv_buffer, index=False)
        csv_bytes = csv_buffer.getvalue().encode('utf-8')

        # Download button with dynamic filename
        st.download_button(
            label=f"💾 Download generated CSV ({export_filename})",
            data=csv_bytes,
            file_name=export_filename,
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"Error processing tab structure: {e}")
