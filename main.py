import streamlit as st
import tempfile
import os
from dotenv import load_dotenv
load_dotenv()  # Charge les variables du .env


from extract_data_organigram import (
    convert_avif_to_png,
    extract_from_image,
    extract_organigramme_from_pdf_in_memory,
)

# 💡 API key depuis .env ou configuration sécurisée
API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    st.error("Aucune clé OpenAI trouvée dans les variables d'environnement. Merci de configurer OPENAI_API_KEY dans les secrets Streamlit Cloud.")
    st.stop()



st.set_page_config(page_title="Extraction d'organigrammes", page_icon="📄")
st.title("📄 Extraction d'organigramme PDF ou image → Excel")

uploaded_file = st.file_uploader(
    "Dépose ton fichier (PDF ou image)",
    type=["pdf", "png", "jpg", "jpeg", "avif"]
)
client_name = st.text_input("Nom du client (facultatif)")

# 🧠 Cache le traitement PDF
@st.cache_data(show_spinner="🔍 Traitement du PDF en cours...")
def get_excel_file_from_pdf(file_bytes, api_key, client_name):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        return extract_organigramme_from_pdf_in_memory(tmp.name, api_key=api_key, client_name=client_name)

if uploaded_file:
    st.success(f"📁 Fichier importé : `{uploaded_file.name}`")

    if st.button("🚀 Lancer l'extraction"):
        file_bytes = uploaded_file.read()
        filename = uploaded_file.name.lower()

        # 🔄 Conversion AVIF → PNG
        if filename.endswith(".avif"):
            st.info("Conversion AVIF → PNG en cours...")
            file_bytes = convert_avif_to_png(file_bytes)
            if file_bytes is None:
                st.error("❌ Échec de la conversion AVIF.")
                st.stop()
            filename = filename.replace(".avif", ".png")
            st.success("✅ Conversion réussie.")

        # 🧾 PDF
        if filename.endswith(".pdf"):
            excel_file = get_excel_file_from_pdf(file_bytes, api_key=API_KEY, client_name=client_name)

        # 🖼️ Image
        elif filename.endswith((".png", ".jpg", ".jpeg")):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(file_bytes)
                with st.spinner("🖼️ Traitement de l'image en cours..."):
                    excel_file = extract_from_image(tmp.name, api_key=API_KEY, client_name=client_name)

        else:
            st.error("❌ Format de fichier non pris en charge.")
            st.stop()

        # 📥 Résultat
        if excel_file:
            st.download_button(
                label="📥 Télécharger le fichier Excel",
                data=excel_file,
                file_name="organigramme.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("❌ Aucune donnée extraite.")
