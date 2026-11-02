# DocuIntel AI · Document Intelligence & Invoice Review

An independent, open-source **Python portfolio prototype** that extracts invoice fields from text-based PDFs, applies explainable validation rules, detects duplicates across an uploaded batch, records reviewer decisions in **SQLite**, and exports a review-ready CSV report.

> **Honest technical description:** Despite the project name, this version uses *deterministic PDF text extraction and rule-based checks*, not generative AI or a trained machine-learning model. The initial implementation was AI-assisted and should be reviewed and modified by the repository owner before presenting it as their own work.

## Features

- Multi-PDF upload (up to 20 files, 5 MB each)
- PDF text extraction using `pdfplumber`
- Field identification for invoice number, vendor, invoice date, due date, and total
- Missing field, date-order, large-amount, duplicate-file, and repeated-vendor/invoice-number flags
- Document investigation view and explanation of flags
- Reviewer status and notes persisted to local SQLite
- Downloadable batch review report in CSV format
- Three fabricated sample PDF invoices; **no real vendor or government records**

## Run locally (free)

Requirements: Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL printed by Streamlit, typically http://localhost:8501.

Upload the PDF documents from `samples/` to try the workflow. The duplicate sample is deliberately labeled as a potential duplicate, and the high-value sample illustrates the $90,000 review threshold.

## Test

```bash
pip install pytest
pytest -q
```

## Free deployment

This app is designed to run locally or on Streamlit Community Cloud. For public cloud demos, **only use synthetic PDFs**: uploaded documents are processed by the hosting server, and SQLite files on free hosting are not a persistent or user-isolated production database.

1. Push this folder's contents to a public GitHub repository.
2. Visit https://share.streamlit.io/ and create a free app from your repository.
3. Set the entry point to `app.py`.
4. Share the resulting hosted link after checking all features.

No OpenAI API key, payment method, or paid subscription is needed for the local prototype. Free hosting availability and limits can change.

## How validation works

| Check | What triggers a review flag |
|---|---|
| Missing fields | Invoice number, vendor, date, or total not recognized |
| High value | Total >= $90,000 (illustrative threshold) |
| Due-date order | Due date earlier than invoice date |
| Exact duplicate | Identical PDF bytes within the current upload batch |
| Business-key repeat | Same vendor and invoice number within the batch |

**These flags are not evidence of fraud.** Validate against original documents and applicable policies before making decisions.

## Technical limitations and privacy

- Requires selectable PDF text; scanned PDFs need OCR (not included).
- Templates with different field labels may not extract correctly.
- Duplicate checking covers the current batch only.
- SQLite saves review metadata by file hash; raw uploaded PDFs are not written to SQLite.
- This demo is not intended for sensitive customer, financial, or government records.
- On public hosting, SQLite may be reset and is not a secure multiuser store.

## Tech stack

Python · Streamlit · pdfplumber · pandas · SQLite · pytest

Independent student portfolio demo. Not affiliated with Inalab, the U.S. government, or any procurement agency.
