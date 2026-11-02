"""Deterministic invoice extraction, validation, and explainable review scoring.

No language model is used. This is a document-intelligence prototype, not a fraud detector.
"""
import hashlib
import io
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

import pdfplumber

PATTERNS = {
    'invoice_number': [r'(?im)^\s*(?:invoice\s*(?:number|no\.?|#)|inv\s*#)\s*[:#-]?\s*([A-Za-z0-9-]{3,40})\s*$'],
    'vendor': [r'(?im)^\s*(?:vendor|supplier|from)\s*:\s*(.{2,100}?)\s*$'],
    'invoice_date': [r'(?im)^\s*(?:invoice\s*date|date\s*issued|date)\s*:\s*(\d{4}-\d{2}-\d{2})\s*$'],
    'due_date': [r'(?im)^\s*(?:due\s*date|payment\s*due)\s*:\s*(\d{4}-\d{2}-\d{2})\s*$'],
    'amount': [r'(?im)^\s*(?:total\s*due|invoice\s*total|total\s*amount|amount\s*due)\s*:\s*\$?\s*([0-9,]+\.\d{2})\s*$'],
}

@dataclass
class Invoice:
    filename: str
    sha256: str
    invoice_number: str = ''
    vendor: str = ''
    invoice_date: str = ''
    due_date: str = ''
    amount: str = ''
    extracted_text: str = ''
    issues: list[str] = field(default_factory=list)
    priority: str = 'Low'
    extraction_status: str = 'Complete'

    def as_record(self):
        return {k: getattr(self,k) for k in ('filename','sha256','invoice_number','vendor','invoice_date','due_date','amount','priority','extraction_status')}


def extract_pdf(data: bytes, filename: str) -> Invoice:
    item = Invoice(filename=filename, sha256=hashlib.sha256(data).hexdigest())
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            if len(pdf.pages) > 20:
                raise ValueError('PDF exceeds 20-page limit')
            item.extracted_text = '\n'.join((page.extract_text() or '') for page in pdf.pages)
    except Exception as exc:
        item.extraction_status = 'Unreadable PDF'
        item.issues.append('PDF could not be read: '+str(exc)[:100])
        item.priority = 'High'
        return item
    if not item.extracted_text.strip():
        item.extraction_status = 'No selectable text'
        item.issues.append('Scanned or image-only PDF: OCR is not included')
        item.priority = 'High'
        return item
    for key, candidates in PATTERNS.items():
        for pattern in candidates:
            match = re.search(pattern, item.extracted_text)
            if match:
                setattr(item, key, match.group(1).strip())
                break
    validate(item)
    return item


def validate(item: Invoice) -> None:
    issues = []
    required = {'invoice_number':'invoice number', 'vendor':'vendor', 'invoice_date':'invoice date', 'amount':'total amount'}
    for key, label in required.items():
        if not getattr(item,key):
            issues.append('Missing '+label)
    amount = None
    if item.amount:
        try:
            amount = Decimal(item.amount.replace(',',''))
            if amount <= 0:
                issues.append('Non-positive invoice amount')
            if amount >= Decimal('90000'):
                issues.append('High-value invoice ($90,000 or more; illustrative threshold)')
        except InvalidOperation:
            issues.append('Invalid invoice amount')
    parsed = {}
    for key in ('invoice_date','due_date'):
        val = getattr(item,key)
        if val:
            try:
                parsed[key] = date.fromisoformat(val)
            except ValueError:
                issues.append('Invalid '+key.replace('_',' '))
    if 'invoice_date' in parsed and 'due_date' in parsed and parsed['due_date'] < parsed['invoice_date']:
        issues.append('Due date precedes invoice date')
    item.issues = issues
    item.priority = 'High' if any(s.startswith(('Missing','Invalid','Non-positive','High-value','Due date')) for s in issues) else 'Low'


def analyze_batch(items: list[Invoice]) -> list[Invoice]:
    """Cross-file review checks. Duplicate candidates aren't accusations of fraud."""
    seen_hash, seen_key = {}, {}
    for item in items:
        if item.extraction_status != 'Complete':
            continue
        key = (item.vendor.strip().casefold(), item.invoice_number.strip().casefold())
        if item.sha256 in seen_hash:
            item.issues.append('Exact duplicate file in this batch')
        else:
            seen_hash[item.sha256] = item.filename
        if all(key) and key in seen_key:
            item.issues.append('Repeated vendor + invoice number in this batch')
        elif all(key):
            seen_key[key] = item.filename
        if item.issues:
            item.priority = 'High'
    return items
