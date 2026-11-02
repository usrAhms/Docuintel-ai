"""Run with: streamlit run app.py"""
import io
import os
import pandas as pd
import streamlit as st
from src.core import extract_pdf, analyze_batch
from src.storage import connection, get_review, save_review

st.set_page_config(page_title='DocuIntel AI | Invoice Review', page_icon='📄', layout='wide')
st.markdown('''<style>.block-container{padding-top:2rem;max-width:1200px}.hero{padding:25px 30px;border-radius:18px;background:linear-gradient(120deg,#142b47,#1d5272);color:#fff;margin-bottom:18px}.hero h1{margin:0;font-size:40px}.hero p{color:#d4e7f3;margin:12px 0 0}.hint{font-size:13px;color:#64748b}</style>''', unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>DocuIntel AI</h1><p>Extract. Validate. Investigate. Document decisions.</p></div>', unsafe_allow_html=True)
st.caption('Independent portfolio prototype • Rule-based document intelligence (not generative AI) • Synthetic test invoices • Not affiliated with Inalab or a government agency')

with st.sidebar:
    st.header('Workflow')
    st.markdown('**1.** Upload text-based PDF invoices  \n**2.** Inspect extracted fields and review flags  \n**3.** Record decisions in SQLite  \n**4.** Download a CSV report')
    st.divider()
    st.info('No external API keys required. PDFs are processed locally by the Python process. The app does not retain uploaded PDF bytes in SQLite.')
    st.warning('On shared cloud hosting, local SQLite files may be ephemeral or shared across sessions. Use synthetic documents only in the public demo.')
    st.download_button('Download example CSV schema', 'invoice_number,vendor,invoice_date,due_date,amount\n', file_name='invoice-fields.csv')

st.subheader('01 / Upload invoices')
files = st.file_uploader('Choose up to 20 text-based PDF invoices (max 5 MB each)', type=['pdf'], accept_multiple_files=True)
if files:
    if len(files)>20:
        st.error('Please upload 20 or fewer PDFs.')
        st.stop()
    items=[]
    for file in files:
        data=file.getvalue()
        if len(data)>5_000_000:
            st.warning(f'{file.name}: file exceeds 5 MB and was skipped')
            continue
        items.append(extract_pdf(data,file.name))
    analyze_batch(items)
    if not items:
        st.stop()
    st.session_state['items']=items
else:
    items=st.session_state.get('items',[])
    if items:
        st.info('Displaying the previous upload from this session. Upload new files to replace the batch.')

if not items:
    st.info('Start with the included sample PDF invoices in the `samples/` folder. Download the project ZIP, then upload those PDF files here.')
    st.stop()

st.subheader('02 / Batch overview')
c1,c2,c3,c4=st.columns(4)
c1.metric('Documents', len(items))
c2.metric('High-priority', sum(x.priority=='High' for x in items))
c3.metric('Needs extraction help',sum(x.extraction_status!='Complete' for x in items))
c4.metric('Potential duplicates',sum(any('duplicate' in y.lower() or 'Repeated vendor' in y for y in x.issues) for x in items))
rows=[{**x.as_record(),'issues':'; '.join(x.issues) or 'No flags'} for x in items]
dataframe=pd.DataFrame(rows)
st.dataframe(dataframe.drop(columns=['sha256']),use_container_width=True,hide_index=True)

st.subheader('03 / Investigate and review')
index=st.selectbox('Select document',range(len(items)),format_func=lambda i:f'{items[i].filename} — {items[i].priority} priority')
item=items[index]
left,right=st.columns([1,1])
with left:
    st.markdown('#### Extracted fields')
    for label,value in [('Invoice number',item.invoice_number),('Vendor',item.vendor),('Invoice date',item.invoice_date),('Due date',item.due_date),('Total amount',item.amount)]:
        st.write(f'**{label}:** {value or "Not extracted"}')
    st.markdown('#### Explainable review flags')
    if item.issues:
        for issue in item.issues: st.warning(issue)
    else: st.success('No flags under the sample validation rules. This does not mean the invoice is valid.')
    with st.expander('Raw extracted text'):
        st.code(item.extracted_text[:12000] or '(No selectable text)',language='text')
with right:
    st.markdown('#### Reviewer decision')
    db_path=os.environ.get('DOCUINTEL_DB','docuintel_reviews.sqlite3')
    try:
        db=connection(db_path)
    except Exception as exc:
        st.error(f'Could not open SQLite database: {exc}')
        st.stop()
    prior=get_review(db,item.sha256) or {}
    statuses=['Unreviewed','Needs follow-up','Cleared']
    with st.form(f'review-{item.sha256}'):
        status=st.selectbox('Status',statuses,index=statuses.index(prior.get('status','Unreviewed')))
        reviewer=st.text_input('Reviewer (optional)',value=prior.get('reviewer',''),max_chars=80)
        notes=st.text_area('Investigation notes',value=prior.get('notes',''),max_chars=2000)
        submitted=st.form_submit_button('Save decision',type='primary')
    if submitted:
        save_review(db,item.sha256,status,reviewer,notes)
        st.success('Review saved in SQLite on this server.')
    st.caption('Reviews are keyed by PDF file hash, not by customer identity.')

st.subheader('04 / Download report')
report=[]
for x in items:
    review=get_review(db,x.sha256) or {}
    report.append({**x.as_record(),'issues':'; '.join(x.issues),'review_status':review.get('status','Unreviewed'),'reviewer':review.get('reviewer',''),'review_notes':review.get('notes','')})
output=pd.DataFrame(report).to_csv(index=False).encode('utf-8-sig')
st.download_button('Download batch review report (CSV)',data=output,file_name='docuintel-review-report.csv',mime='text/csv',type='primary')
st.caption('Limitations: only text-based PDFs with recognizable English labels; no OCR or LLM; extracted values must be manually verified. Flags are demonstration heuristics, not fraud allegations or compliance determinations.')
