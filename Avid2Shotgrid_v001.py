import streamlit as st
import pandas as pd
import io
import os
from datetime import datetime

def convert_dataframe(df_source):
    df_target = pd.DataFrame()
    
    # Alle Spaltennamen von unsichtbaren Zeichen (\t, \r, Leerzeichen) befreien
    df_source.columns = df_source.columns.astype(str).str.strip()
    
    # Sicherheits-Check für die Benutzeroberfläche
    required_columns = ['Name', 'Frame Count Start', 'Frame Count End', 'handles', 'Frame Count Duration']
    missing_columns = [col for col in required_columns if col not in df_source.columns]
    
    if missing_columns:
        st.error(f"Schwerwiegender Fehler: Benötigte Spalten wurden nicht gefunden: {missing_columns}")
        st.info(f"Gefundene Spalten in der Datei sind: {list(df_source.columns[:10])}...")
        st.stop()
        
    # Inhalte bereinigen und in Zahlen umwandeln
    df_source['Name'] = df_source['Name'].astype(str).str.strip()
    df_source['Frame Count Start'] = pd.to_numeric(df_source['Frame Count Start'], errors='coerce')
    df_source['Frame Count End'] = pd.to_numeric(df_source['Frame Count End'], errors='coerce')
    df_source['handles'] = pd.to_numeric(df_source['handles'], errors='coerce').fillna(0)
    df_source['Frame Count Duration'] = pd.to_numeric(df_source['Frame Count Duration'], errors='coerce')
    
    # --- TRANSFORMATIONSLOGIK ---
    
    # 1. Quelle Name die ersten 17 Zeichen -> Ziel Link
    df_target['Link'] = df_source['Name'].str[:17]
    
    # 2. Quelle Name komplett -> Ziel File name
    df_target['File name'] = df_source['Name']
    
    # 3. LEER: Format File Type
    df_target['Format File Type'] = "" 
    
    # 4. Quelle Frame Count Start - handles -> Ziel First frame Frame in
    df_target['First frame Frame in'] = df_source['Frame Count Start'] - df_source['handles']
    
    # 5. Quelle Frame Count End + handles -> Ziel Last frame Frame Out
    df_target['Last frame Frame Out'] = df_source['Frame Count End'] + df_source['handles']
    
    # 6. Quelle Frame Count Duration + 2 * handles -> Ziel Working duration Frame Count
    df_target['Working duration Frame Count'] = df_source['Frame Count Duration'] + (2 * df_source['handles'])
    
    # 7. LEER: Description, Submitted For, Artist und Submission
    df_target['Description'] = ""
    df_target['Submitted For'] = ""
    df_target['Artist'] = ""
    df_target['Submission'] = ""
    
    # Formatierung zu Ganzzahlen (Int) ohne Dezimalstellen (.0)
    for col in ['First frame Frame in', 'Last frame Frame Out', 'Working duration Frame Count']:
        df_target[col] = df_target[col].fillna(0).astype(int)
        
    return df_target

# --- Streamlit Benutzeroberfläche ---
st.set_page_config(page_title="VFX Shotlist Converter", layout="wide")

st.title("🎬 VFX Tab-Delimited Shotlist Converter")
st.write("Wandelt die tabulatorgetrennte Quelldatei direkt in das KLR-Zielformat für ShotGrid um.")

uploaded_file = st.file_uploader("Tab-Delimited Quelldatei (.txt) hochladen", type=["txt"])

if uploaded_file is not None:
    try:
        # Dynamischen Dateinamen für den Export generieren
        base_filename = os.path.splitext(uploaded_file.name)[0]
        current_date = datetime.now().strftime("%y%m%d")
        export_filename = f"{base_filename}_toShotgrid_{current_date}_v01.csv"
        
        # Datei als Binärdaten auslesen
        raw_bytes = uploaded_file.getvalue()
        
        # Verbesserte Encoding-Erkennung
        try:
            text_content = raw_bytes.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                text_content = raw_bytes.decode('utf-16')
            except UnicodeDecodeError:
                text_content = raw_bytes.decode('latin-1', errors='ignore')
            
        # Zeilenumbrüche vereinheitlichen
        lines = [line for line in text_content.replace('\r\n', '\r').replace('\n', '\r').split('\r') if line.strip()]
        
        # Jede Zeile am Tabulator trennen
        parsed_data = [line.split('\t') for line in lines]
        
        # Header und Daten trennen
        header = [col.strip() for col in parsed_data[0]]
        data_rows = parsed_data[1:]
        
        # Spaltenanzahl angleichen
        adjusted_rows = []
        for row in data_rows:
            if len(row) < len(header):
                row += [""] * (len(header) - len(row))
            elif len(row) > len(header):
                row = row[:len(header)]
            adjusted_rows.append(row)
            
        # DataFrame erstellen
        df_source = pd.DataFrame(adjusted_rows, columns=header)
        df_source.columns = df_source.columns.astype(str).str.strip()
        
        # Konvertierung ausführen
        df_converted = convert_dataframe(df_source)
        
        # Vorschau anzeigen
        st.subheader("Vorschau der konvertierten KLR-Liste:")
        st.dataframe(df_converted)
        
        # CSV im Speicher für den Download vorbereiten
        csv_buffer = io.StringIO()
        df_converted.to_csv(csv_buffer, index=False)
        csv_bytes = csv_buffer.getvalue().encode('utf-8')
        
        # Download-Button bereitstellen mit dem dynamischen Dateinamen
        st.download_button(
            label=f"💾 Generierte CSV ({export_filename}) herunterladen",
            data=csv_bytes,
            file_name=export_filename,
            mime="text/csv"
        )
        
    except Exception as e:
        st.error(f"Fehler bei der Verarbeitung der Tab-Struktur: {e}")
