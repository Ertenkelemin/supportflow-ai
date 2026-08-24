from __future__ import annotations

from html import escape

import streamlit as st

from app.analyzer import AnalysisError
from app.config import get_settings
from app.models import AnalysisResult, TicketRequest
from app.service import SupportFlowService

SAMPLE_SUBJECT = "Charged twice and still cannot access my Pro plan"
SAMPLE_MESSAGE = """I upgraded to Pro yesterday, but my card was charged twice and the account still shows the Free plan. I already sent screenshots to support and have not received an answer. I need this fixed today or I will dispute both charges with my bank."""
SAMPLE_CUSTOMER = "Premium customer for 18 months. No previous payment disputes. Account ID: demo-4821."
SAMPLE_POLICY = """Billing Operations must verify transaction IDs before confirming a duplicate charge. Confirmed duplicate charges are eligible for a refund, normally processed in 5-7 business days. Chargeback threats require human escalation. Never request full card details in a support reply."""

st.set_page_config(
    page_title="SupportFlow AI",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background:#f6f4ef; color:#172b33; }
    header[data-testid="stHeader"] { display:none; }
    main .block-container { padding-top:2rem; max-width:1180px; }
    [data-testid="stSidebar"] { background:#0d2732; }
    [data-testid="stSidebar"] * { color:#eef8f6; }
    [data-testid="stSidebar"] hr { border-color:rgba(255,255,255,.16); }
    [data-testid="stSidebar"] input[role="combobox"] {
        background:#071b23 !important; color:#eef8f6 !important;
        -webkit-text-fill-color:#eef8f6 !important; border:0 !important;
    }
    [data-testid="stSidebar"] [role="group"]:has(input[role="combobox"]) {
        background:#071b23 !important; border-color:#23414c !important;
    }
    [data-testid="stSidebar"] button[aria-label="Open"] {
        background:#071b23 !important; color:#eef8f6 !important;
    }
    .hero {
        padding:clamp(1.9rem,5vw,3.2rem); border-radius:26px; color:white;
        background:radial-gradient(circle at 88% 20%,rgba(247,137,82,.75),transparent 28%),
                   linear-gradient(135deg,#0d3440,#17606a);
        box-shadow:0 20px 55px rgba(13,52,64,.2); margin-bottom:1.6rem;
    }
    .hero .kicker { color:#b9eee5; letter-spacing:.14em; font-size:.74rem; font-weight:800; }
    .hero h1 { font-size:clamp(2.15rem,5vw,3.5rem); line-height:1.02; margin:.65rem 0 1rem; }
    .hero p { color:#e6f7f4; max-width:735px; font-size:1.02rem; }
    .model-pill {
        display:inline-flex; align-items:center; gap:.4rem; padding:.3rem .7rem;
        border-radius:99px; background:#dff3ee; color:#17606a;
        font-size:.74rem; font-weight:800;
    }
    .model-pill::before { content:""; width:.42rem; height:.42rem; border-radius:50%; background:#3ba776; }
    .routing-grid {
        display:grid; grid-template-columns:repeat(auto-fit,minmax(145px,1fr));
        gap:.65rem; margin:.9rem 0 1.2rem;
    }
    .routing-item { background:#fff; border:1px solid #dedbd3; border-radius:13px; padding:.8rem .9rem; }
    .routing-item span { display:block; color:#778187; font-size:.66rem; font-weight:800; letter-spacing:.08em; }
    .routing-item strong { display:block; color:#173b43; font-size:.96rem; margin-top:.25rem; }
    [data-testid="stTextInputRootElement"], [data-testid="stTextAreaRootElement"] {
        background:#fff !important; border:1px solid #c9d0cd !important;
        border-radius:10px !important; box-shadow:none !important;
    }
    [data-testid="stTextInputRootElement"]:focus-within,
    [data-testid="stTextAreaRootElement"]:focus-within { border-color:#198071 !important; }
    [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {
        background:#fff !important; color:#172b33 !important;
        -webkit-text-fill-color:#172b33 !important; border:0 !important;
        outline:0 !important; box-shadow:none !important; caret-color:#198071 !important;
    }
    [data-testid="stMain"] [data-testid="stBaseButton-secondary"] {
        background:#fff !important; border-color:#b9d6d0 !important; color:#17606a !important;
    }
    [data-testid="stMain"] [data-testid="stBaseButton-secondary"] p { color:#17606a !important; }
    [data-testid="stExpander"] { background:#fff; border-color:#dedbd3; border-radius:12px; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_service() -> SupportFlowService:
    return SupportFlowService()


def load_sample() -> None:
    st.session_state.customer_tier = "Premium"
    st.session_state.reply_tone = "Professional"
    st.session_state.subject = SAMPLE_SUBJECT
    st.session_state.message = SAMPLE_MESSAGE
    st.session_state.customer_context = SAMPLE_CUSTOMER
    st.session_state.policy_context = SAMPLE_POLICY
    st.session_state.result = None


service = get_service()
settings = get_settings()

for key, default in {
    "subject": "",
    "message": "",
    "customer_context": "",
    "policy_context": "",
    "result": None,
    "customer_tier": "Standard",
    "reply_tone": "Professional",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

with st.sidebar:
    st.markdown("## ◆ SupportFlow")
    st.caption("AI SUPPORT OPERATIONS")
    st.markdown("---")
    customer_tier = st.selectbox(
        "Customer tier", ["Standard", "Premium", "Enterprise"], key="customer_tier"
    )
    reply_tone = st.selectbox(
        "Reply tone", ["Professional", "Friendly", "Concise"], key="reply_tone"
    )
    customer_context = st.text_area(
        "Customer context",
        key="customer_context",
        placeholder="Plan, history, account details...",
        height=105,
    )
    policy_context = st.text_area(
        "Policy context",
        key="policy_context",
        placeholder="Refund, escalation, and SLA rules...",
        height=150,
    )
    st.markdown("---")
    st.success(f"Local Ollama · {settings.ollama_model}")
    st.caption("Human approval remains required")

st.markdown(
    """
    <section class="hero">
      <div class="kicker">TRIAGE FASTER · RESPOND SAFELY</div>
      <h1>Turn support tickets<br/>into clear next actions.</h1>
      <p>SupportFlow classifies incoming requests, routes them by risk and priority, drafts a policy-aware reply, and produces an integration-ready automation payload.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

heading_col, sample_col = st.columns([4, 1])
with heading_col:
    st.markdown("### Analyze a customer ticket")
with sample_col:
    st.button("Use sample", on_click=load_sample, use_container_width=True)

with st.form("ticket_form"):
    subject = st.text_input(
        "Subject",
        key="subject",
        placeholder="Unable to access paid plan",
        label_visibility="collapsed",
    )
    message = st.text_area(
        "Customer message",
        key="message",
        placeholder="Paste the customer's message...",
        height=210,
        label_visibility="collapsed",
    )
    submitted = st.form_submit_button(
        "Analyze and route ticket",
        type="primary",
        use_container_width=True,
    )

if submitted:
    if len(subject.strip()) < 3 or len(message.strip()) < 20:
        st.error("Add a subject and a customer message with at least 20 characters.")
    else:
        request_data = TicketRequest(
            subject=subject,
            message=message,
            customer_tier=customer_tier,
            customer_context=customer_context,
            policy_context=policy_context,
            reply_tone=reply_tone,
        )
        try:
            with st.spinner("Classifying intent, risk, and routing..."):
                st.session_state.result = service.analyze(request_data)
        except AnalysisError as error:
            st.error(str(error))

result: AnalysisResult | None = st.session_state.result
if result:
    analysis = result.analysis
    st.markdown('<span class="model-pill">OLLAMA · STRUCTURED TRIAGE</span>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="routing-grid">
          <div class="routing-item"><span>CATEGORY</span><strong>{escape(analysis.category)}</strong></div>
          <div class="routing-item"><span>PRIORITY</span><strong>{escape(analysis.priority)}</strong></div>
          <div class="routing-item"><span>ROUTE TO</span><strong>{escape(analysis.routing_team)}</strong></div>
          <div class="routing-item"><span>SENTIMENT</span><strong>{escape(analysis.sentiment)}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    triage_tab, reply_tab, automation_tab = st.tabs(
        ["Triage decision", "Draft reply", "Automation payload"]
    )

    with triage_tab:
        st.caption(f"{result.ticket_id} · Confidence {analysis.confidence:.0%}")
        st.markdown("#### Summary")
        st.write(analysis.summary)
        if analysis.escalation_required:
            st.warning(f"Human escalation required: {analysis.escalation_reason}")
        left, right = st.columns(2)
        with left:
            st.markdown("#### Risk flags")
            if analysis.risk_flags:
                for flag in analysis.risk_flags:
                    st.markdown(f"- {flag}")
            else:
                st.caption("No additional risk flags detected.")
        with right:
            st.markdown("#### Next actions")
            for index, action in enumerate(analysis.next_actions, start=1):
                st.markdown(f"{index}. {action}")
        st.markdown("#### Tags")
        st.code(", ".join(analysis.tags), language=None)

    with reply_tab:
        st.info("Draft only — review before sending to the customer.")
        st.markdown("#### Suggested response")
        st.write(analysis.draft_reply)

    with automation_tab:
        st.caption("Example payload for Zendesk, Intercom, Freshdesk, or a custom CRM workflow.")
        st.code(result.automation_payload.model_dump_json(indent=2), language="json")

    st.download_button(
        "Download analysis · JSON",
        data=service.export_json(result),
        file_name=f"{result.ticket_id.lower()}-analysis.json",
        mime="application/json",
        use_container_width=True,
    )

st.markdown("---")
st.caption("Built for safe triage automation, policy-aware drafting, and human review.")
