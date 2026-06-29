from flask import Flask, render_template, request, send_file, redirect, url_for, flash
import pandas as pd
import requests
from urllib.parse import quote
from pathlib import Path
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

UPLOAD_FOLDER = Path("uploads")
OUTPUT_FOLDER = Path("outputs")
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {"xlsx"}

DATA_ENTRY_SHEET = "Data Entry"
CAS_COLUMN = "CAS Number"

PUBCHEM_FIELDS = [
    "IUPACName",
    "MolecularFormula",
    "MolecularWeight",
    "CanonicalSMILES",
    "IsomericSMILES",
    "InChIKey"
]

DATA_ENTRY_COLUMNS = [
    "TPN#", "Salt", "Synonym", "SMILES", "Date", "Vendor/Supplier",
    "2D Barcode", "Container Type", "Stock type", "Physical State",
    "Amount", "Units", "Expiration date", "Supplier Synonym",
    "Supplier Lot Number", "CAS Number", "Person", "Note",
    "Manufacturer", "Supplier FW", "Purity (%)", "Purification Method",
    "MSDS Link", "Location", "Location(Sub)", "Location",
    "IUPACName", "MolecularFormula", "MolecularWeight",
    "CanonicalSMILES", "IsomericSMILES", "InChIKey", "Status"
]

CDD_UPLOAD_COLUMNS = [
    "TPN#", "Salt", "Synonym", "SMILES", "IP Owner", "CAS Number",
    "Date", "Person", "Note", "Vendor/Supplier", "Manufacturer",
    "Supplier Lot Number", "Supplier Synonym", "Supplier FW",
    "Purity (%)", "Purification Method", "Sample ID",
    "Supplier Synonym", "Shipment Date", "Expiration Date",
    "Amount", "Units", "2D Barcode", "Container Type",
    "Stock Type", "Physical State"
]


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def fetch_pubchem_by_cas(cas):
    url = (
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
        + quote(cas)
        + "/property/"
        + ",".join(PUBCHEM_FIELDS)
        + "/JSON"
    )

    response = requests.get(url, timeout=20)

    if response.status_code != 200:
        return None

    data = response.json()
    return data["PropertyTable"]["Properties"][0]


def process_excel(input_path, output_path):
    df = pd.read_excel(input_path, sheet_name=DATA_ENTRY_SHEET)

    for col in DATA_ENTRY_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    for index, row in df.iterrows():
        cas = str(row.get(CAS_COLUMN, "")).strip()

        if cas == "" or cas.lower() == "nan":
            df.loc[index, "Status"] = "No CAS"
            continue

        try:
            props = fetch_pubchem_by_cas(cas)

            if not props:
                df.loc[index, "Status"] = "Not found"
                continue

            for field in PUBCHEM_FIELDS:
                df.loc[index, field] = props.get(field, "")

            if str(df.loc[index, "SMILES"]).strip() == "":
                df.loc[index, "SMILES"] = props.get("CanonicalSMILES", "")

            if str(df.loc[index, "Supplier FW"]).strip() == "":
                df.loc[index, "Supplier FW"] = props.get("MolecularWeight", "")

            df.loc[index, "Status"] = "Found"

        except Exception as e:
            df.loc[index, "Status"] = f"Error: {e}"

    df_data_entry = df[DATA_ENTRY_COLUMNS]

    cdd = pd.DataFrame(columns=CDD_UPLOAD_COLUMNS)

    for col in CDD_UPLOAD_COLUMNS:
        if col in df.columns:
            cdd[col] = df[col]
        else:
            cdd[col] = ""

    cdd["Stock Type"] = df.get("Stock type", "")
    cdd["Expiration Date"] = df.get("Expiration date", "")

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df_data_entry.to_excel(writer, sheet_name="Data Entry", index=False)
        cdd.to_excel(writer, sheet_name="CDD Upload", index=False)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process_file():
    if "file" not in request.files:
        flash("Please upload an Excel file.")
        return redirect(url_for("home"))

    file = request.files["file"]

    if file.filename == "":
        flash("Please select a file.")
        return redirect(url_for("home"))

    if not allowed_file(file.filename):
        flash("Only .xlsx files are supported.")
        return redirect(url_for("home"))

    safe_name = secure_filename(file.filename)
    unique_id = uuid.uuid4().hex[:8]
    input_path = UPLOAD_FOLDER / f"{unique_id}_{safe_name}"
    output_path = OUTPUT_FOLDER / f"cdd_pubchem_filled_{unique_id}.xlsx"

    file.save(input_path)

    try:
        process_excel(input_path, output_path)
    except Exception as e:
        flash(f"Could not process file: {e}")
        return redirect(url_for("home"))

    return send_file(output_path, as_attachment=True, download_name="cdd_pubchem_filled.xlsx")


if __name__ == "__main__":
    app.run(debug=True)