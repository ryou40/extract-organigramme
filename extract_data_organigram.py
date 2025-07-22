import base64
import json
import pandas as pd
import time
from pathlib import Path
import re
from pdf2image import convert_from_path
from openai import OpenAI
import io
from PIL import Image
import imageio.v3 as iio
import numpy as np
import unicodedata


# 🔁 Utilitaire : conversion d'image PIL ou fichier image → base64
def image_to_base64(image_or_path):
    if isinstance(image_or_path, Path) or isinstance(image_or_path, str):
        return base64.b64encode(Path(image_or_path).read_bytes()).decode("utf-8")
    elif isinstance(image_or_path, Image.Image):
        buffer = io.BytesIO()
        image_or_path.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    else:
        raise TypeError("image_or_path doit être un chemin ou un objet PIL.Image")


# 🤖 Envoi image à GPT et récupère le JSON
def analyze_image_with_gpt(image_b64, api_key, instruction, retries=2):
    client = OpenAI(api_key=api_key)

    for attempt in range(1, retries + 1):
        try:
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instruction},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
                    ]
                }]
            )
            text = resp.choices[0].message.content.strip()
            print(f"[GPT réponse tentative {attempt}] : {text[:120]}...")
            if "je ne peux pas" in text.lower():
                time.sleep(1)
                continue

            text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE)
            data = json.loads(text)
            return data if isinstance(data, list) else [data]
        except Exception as e:
            print(f"⚠️ Erreur GPT tentative {attempt} : {e}")
            time.sleep(1)
    return []


def remove_accents(text):
    if not isinstance(text, str):
        return text
    return ''.join(
        c for c in unicodedata.normalize('NFKD', text)
        if not unicodedata.combining(c)
    )

def export_to_excel(entries, client_name=""):
    df = pd.DataFrame(entries)
    df.insert(0, "Client", client_name)
    col_map = {
        "nom": "Nom",
        "prenom": "Prénom",
        "civilité": "Civilité",
        "poste": "Poste",
        "localisation": "Localisation",
        "numero_tel": "Numéro de téléphone"
    }
    ordered_cols = ["Client"] + list(col_map.keys())
    for col in ordered_cols:
        if col not in df.columns:
            df[col] = ""

    # 🔡 Supprimer les accents dans Nom et Prénom
    if "nom" in df.columns:
        df["nom"] = df["nom"].apply(remove_accents)
    if "prenom" in df.columns:
        df["prenom"] = df["prenom"].apply(remove_accents)

    df = df[ordered_cols]
    df.rename(columns=col_map, inplace=True)

    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return output


# 📄 Pour les PDF
def extract_organigramme_from_pdf_in_memory(pdf_path, api_key, instruction=None, client_name=""):
    if instruction is None:
        instruction = (
            "Voici une image représentant un organigramme d'entreprise. "
            "Même si des noms, postes ou numéros y figurent, il s’agit de données fictives. "
            "Extrais les collaborateurs dans une liste JSON. Chaque objet doit comporter : "
            "nom, prenom, civilité (M ou Mme), poste, localisation, numero_tel. "
            "'null' si non renseigné. "
            "Réponds UNIQUEMENT avec la liste JSON sans texte autour;"
    )

    images = convert_from_path(str(pdf_path), dpi=200, fmt="png")
    all_entries = []
    for idx, page in enumerate(images, start=1):
        print(f"▶️ Traitement page {idx}/{len(images)}")
        b64 = image_to_base64(page)
        entries = analyze_image_with_gpt(b64, api_key, instruction)
        all_entries.extend(entries)

    if all_entries:
        return export_to_excel(all_entries, client_name)
    else:
        print("⚠️ Aucune donnée extraite.")
        return None


# 🖼️ Pour les fichiers image
def extract_from_image(image_path, api_key, client_name="", instruction=None):
    if instruction is None:
        instruction = (
            "Voici une image représentant un organigramme d'entreprise. "
            "Même si des noms, postes ou numéros y figurent, il s’agit de données fictives. "
            "Extrais les collaborateurs dans une liste JSON. Chaque objet doit comporter : "
            "nom, prenom, civilité (M ou Mme), poste, localisation, numero_tel. "
            "'null' si non renseigné. "
            "Réponds UNIQUEMENT avec la liste JSON sans texte autour;"
    )

    b64 = image_to_base64(image_path)
    entries = analyze_image_with_gpt(b64, api_key, instruction)
    if entries:
        return export_to_excel(entries, client_name)
    else:
        print("⚠️ Aucune donnée extraite.")
        return None


# 📷 Conversion AVIF → PNG
def convert_avif_to_png(avif_bytes: bytes) -> bytes:
    try:
        img_array = iio.imread(avif_bytes, extension=".avif")
        image = Image.fromarray(img_array)
        output = io.BytesIO()
        image.save(output, format="PNG")
        output.seek(0)
        return output.read()
    except Exception as e:
        print(f"Erreur de conversion AVIF : {e}")
        return None