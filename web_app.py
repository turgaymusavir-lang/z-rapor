import csv
import io
import os
from typing import Dict, List

import streamlit as st

from extractor import DocumentExtractor, FIELDS


st.set_page_config(page_title="Muhasebe Belge Cikarim", layout="wide")
st.title("Muhasebe Belge Cikarim (Web)")
st.caption("Belge yukle, alanlari otomatik cikar, tabloyu CSV olarak indir.")

with st.sidebar:
    st.subheader("Ayarlar")
    api_key = st.text_input("OpenAI API Key", value=os.getenv("OPENAI_API_KEY", ""), type="password")
    model = st.text_input("Model", value="gpt-4o-mini")
    st.info("Desteklenen dosyalar: PDF, PNG, JPG, JPEG")

uploads = st.file_uploader(
    "Belgeleri sec",
    type=["pdf", "png", "jpg", "jpeg"],
    accept_multiple_files=True,
)

if "rows" not in st.session_state:
    st.session_state.rows = []

if st.button("Belgeleri Isle", type="primary"):
    if not uploads:
        st.warning("Once en az bir belge sec.")
    elif not api_key.strip():
        st.error("OpenAI API Key gerekli.")
    elif not model.strip():
        st.error("Model alani bos olamaz.")
    else:
        extractor = DocumentExtractor(api_key=api_key.strip(), model=model.strip())
        try:
            with st.spinner("API key dogrulaniyor..."):
                extractor.validate_api_key()
        except Exception as exc:
            st.error(str(exc))
            st.stop()

        rows: List[Dict[str, str]] = []
        progress = st.progress(0)
        status = st.empty()
        total = len(uploads)

        for index, upload in enumerate(uploads, start=1):
            status.text(f"Isleniyor ({index}/{total}): {upload.name}")
            try:
                result = extractor.extract_from_bytes(
                    file_name=upload.name,
                    file_bytes=upload.getvalue(),
                    mime_type=upload.type,
                )
                row = {"Dosya": result.file_name}
                row.update(result.row)
            except Exception as exc:
                row = {"Dosya": upload.name}
                for field in FIELDS:
                    row[field] = ""
                row["Not_Supheli_Alan"] = f"Hata: {exc}"
            rows.append(row)
            progress.progress(index / total)

        status.text("Tamamlandi.")
        st.session_state.rows = rows

if st.session_state.rows:
    st.subheader("Cikarilan Veriler")
    st.dataframe(st.session_state.rows, use_container_width=True)

    csv_buffer = io.StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=["Dosya"] + FIELDS)
    writer.writeheader()
    writer.writerows(st.session_state.rows)
    csv_bytes = csv_buffer.getvalue().encode("utf-8-sig")

    st.download_button(
        label="CSV Indir",
        data=csv_bytes,
        file_name="cikti.csv",
        mime="text/csv",
    )
