# CDD Chemical Data Filler

This is a simple Flask website.

It lets you upload an Excel file with a `Data Entry` sheet.
It reads CAS numbers, pulls available chemical data from NIH PubChem, and downloads a completed Excel file with:

1. Data Entry
2. CDD Upload

## Required input

Your Excel file must contain a sheet called:

Data Entry

It must contain this column:

CAS Number

Other fields can be blank.

## How to run

Install Python packages:

```bash
pip install -r requirements.txt
```

Run the website:

```bash
python app.py
```

Open this in your browser:

```text
http://127.0.0.1:5000
```

## Notes

Some fields come from Quartzy or manual entry, so the app leaves them blank if they are not available from PubChem.
Check salt form and SMILES before uploading to CDD.