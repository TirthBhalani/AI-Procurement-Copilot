from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from src.agents import model_settings
from src.data_access import load_requests, load_employees
from src.solution import analyze_request
from src.security import scrub

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="Procurement Request Copilot", layout="wide")
st.title("Procurement Request Copilot")
st.caption("Evidence first. Recommendations only. Final approvals stay with people.")

by_id = {r['request_id']: r for r in load_requests()}
with st.sidebar:
    st.header("Review workspace")
    source = st.radio("Request source", ["Sample request", "Custom request"])
    request_id = st.selectbox("Request", list(by_id),
                              format_func=lambda rid: f"{rid} - {by_id[rid]['product_name']}")
    architecture = st.radio("Architecture", ['single', 'staged'],
                            format_func=lambda a: "A: Single agent" if a == 'single' else "B: Analyst + reviewer")
    mode = st.selectbox("Execution", ['auto', 'live', 'offline'],
                        help="Auto degrades visibly if the model fails. Live requires a model. Offline checks rules only.")
    provider, model, key = model_settings()
    st.caption(f"Configured model: {provider} / {model}")
    st.caption("Model configured" if key or provider == 'ollama' else "No API key configured; use .env for live AI")
    st.caption("Policy 2026.09 | Reference: 30 September 2026")

req = dict(by_id[request_id])
if source == 'Custom request':
    st.subheader("New purchase request")
    with st.form('request_form'):
        employees = load_employees().fillna('').to_dict(orient='records')
        employee_ids = [e['employee_id'] for e in employees]
        requester = st.selectbox('Requester', employee_ids,
                                  format_func=lambda eid: next(f"{e['name']} ({e['department']})" for e in employees if e['employee_id'] == eid))
        c1, c2 = st.columns(2)
        product = c1.text_input('Product name')
        vendor = c2.text_input('Vendor name')
        category = c1.text_input('Category')
        cost_text = c2.text_input('Annual cost (USD)', help='Leave blank when unknown.')
        users_text = c1.text_input('Number of users/licenses')
        access = c2.selectbox('Intended data access', ['unknown', 'none', 'public', 'internal_documents',
            'internal_marketing', 'source_code', 'production_telemetry', 'confidential_documents',
            'employee_pii', 'customer_pii', 'credentials'])
        purpose = st.text_area('Business purpose and gap in existing tools')
        integrations = st.text_input('Required integrations (comma-separated; blank means none)')
        submitted = st.form_submit_button('Analyze custom request', type='primary')
    req = {'request_id': 'CUSTOM', 'requester_id': requester, 'product_name': product,
           'vendor_name': vendor, 'category': category, 'annual_cost_usd': cost_text or None,
           'user_count': int(users_text) if users_text.isdigit() else None,
           'data_access_level': access, 'business_justification': purpose,
           'requested_integrations': [i.strip() for i in integrations.split(',') if i.strip()]}
else:
    submitted = st.button('Analyze request', type='primary')

req = scrub(req)
fingerprint = json.dumps([req, architecture, mode], sort_keys=True)
if st.session_state.get('fingerprint') != fingerprint:
    st.session_state.pop('decision', None)
    st.session_state['fingerprint'] = fingerprint

if submitted:
    try:
        with st.spinner('Gathering evidence and checking policy...'):
            st.session_state['decision'] = analyze_request(req, architecture, mode=mode).model_dump()
    except Exception:
        st.error('Analysis could not complete. Check the model configuration and local services, or select offline mode. No approval was issued.')

left, right = st.columns([0.85, 1.15], gap='large')
with left:
    st.subheader('Request details')
    st.write('**Product:**', req.get('product_name') or 'Unknown')
    st.write('**Vendor:**', req.get('vendor_name') or 'Unknown')
    st.write('**Annual cost (USD):**', req.get('annual_cost_usd') if req.get('annual_cost_usd') is not None else 'Unknown')
    st.write('**Users/licenses:**', req.get('user_count') or 'Unknown')
    st.write('**Data access:**', req.get('data_access_level') or 'Unknown')
    st.text(req.get('business_justification') or 'Business purpose not supplied')
    with st.expander('Full request'):
        st.json(req)

decision = st.session_state.get('decision')
with right:
    st.subheader('Recommendation and next action')
    if not decision:
        st.info('Analyze a request to see the evidence, required approvals, and next step.')
    else:
        for warning in decision['warnings']:
            st.warning(warning)
        st.subheader(decision['recommendation'])
        st.text(decision['next_step'])
        st.write('**Required human approvals:** ' + ', '.join(decision['required_approvals']))
        st.write('**Risk flags:** ' + (', '.join(decision['risk_flags']) or 'None identified by checks'))
        if decision['missing_information']:
            st.write('**Missing or unverified information**')
            for item in decision['missing_information']:
                st.text('- ' + item)
        st.caption(f"Execution: {decision['execution_mode']} | LLM calls: {decision['telemetry']['llm_calls']} | Tool calls: {decision['telemetry']['tool_calls']}")

if decision:
    evidence_tab, reasoning_tab, handoff_tab = st.tabs(['Evidence', 'AI interpretation', 'Human handoff'])
    with evidence_tab:
        st.dataframe(decision['evidence'], hide_index=True, use_container_width=True)
        with st.expander('Tool and stage trace'):
            st.json(decision['trace'])
    with reasoning_tab:
        if decision['advisory']:
            st.caption('Model interpretation is advisory. Evidence citations validate references, not every sentence; reviewers must verify the reasoning.')
            st.text(decision['advisory']['use_case_summary'])
            st.write('Overlap assessment:', decision['advisory']['overlap_assessment'])
            st.write('Catalog alternatives:', decision['advisory']['alternative_ids'])
            st.write('Evidence indices (zero-based):', decision['advisory']['evidence_indices'])
            for question in decision['advisory']['questions_for_human']:
                st.text('- ' + question)
        else:
            st.info('No model interpretation is available for this run.')
    with handoff_tab:
        st.write('Download this package for the reviewers listed above. This app does not record approvals, purchase software, or change budgets.')
        st.download_button('Download review package', json.dumps(decision, indent=2),
                           file_name=f"{req['request_id']}_{architecture}_review.json", mime='application/json')
        st.download_button('Download handoff note', decision['next_step'],
                           file_name=f"{req['request_id']}_handoff.txt", mime='text/plain')

st.divider()
st.caption('Synthetic assessment data | Tirth')
