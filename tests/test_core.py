from io import BytesIO
from reportlab.pdfgen import canvas
from src.core import extract_pdf, analyze_batch
from src.storage import connection,save_review,get_review


def pdf_bytes(lines):
    buffer=BytesIO(); c=canvas.Canvas(buffer)
    y=750
    for line in lines:
        c.drawString(55,y,line); y-=24
    c.save();return buffer.getvalue()


def test_extract_and_validate():
    b=pdf_bytes(['Vendor: Atlas Supply','Invoice Number: INV-101','Invoice Date: 2026-10-01','Due Date: 2026-10-15','Total Due: $1,240.50'])
    x=extract_pdf(b,'test.pdf')
    assert (x.vendor,x.invoice_number,x.amount,x.priority)==('Atlas Supply','INV-101','1,240.50','Low')


def test_high_value_and_date_rule():
    b=pdf_bytes(['Vendor: Atlas Supply','Invoice Number: INV-102','Invoice Date: 2026-10-20','Due Date: 2026-10-01','Total Due: $95,100.00'])
    x=extract_pdf(b,'test.pdf')
    assert x.priority=='High' and len(x.issues)==2


def test_batch_duplicate():
    b=pdf_bytes(['Vendor: Atlas Supply','Invoice Number: INV-101','Invoice Date: 2026-10-01','Total Due: $1,240.50'])
    items=analyze_batch([extract_pdf(b,'a.pdf'),extract_pdf(b,'b.pdf')])
    assert any('duplicate' in s.lower() for s in items[1].issues)


def test_invalid_pdf():
    item=extract_pdf(b'not a pdf','broken.pdf')
    assert item.priority=='High' and item.extraction_status=='Unreadable PDF'


def test_sqlite_review(tmp_path):
    db=connection(tmp_path/'reviews.sqlite3')
    save_review(db,'abcdef','Needs follow-up','Analyst','Check total against purchase order')
    assert get_review(db,'abcdef')['status']=='Needs follow-up'
