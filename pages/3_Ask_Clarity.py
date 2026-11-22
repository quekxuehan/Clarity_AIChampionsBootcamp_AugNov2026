from datetime import datetime
import re
from urllib.error import URLError

import streamlit as st
from openai import APIError, OpenAI

from app_common import EDUCATIONAL_DISCLAIMER, require_password
from rag import (
    KNOWLEDGE_BASE,
    KnowledgeChunk,
    KnowledgeIndex,
    build_knowledge_index,
    fetch_nea_sources,
    generate_answer,
    retrieve_chunks,
)


@st.cache_resource(show_spinner=False)
def cached_knowledge_index(
    api_key: str, source_chunks: tuple[KnowledgeChunk, ...]
) -> KnowledgeIndex:
    return build_knowledge_index(
        OpenAI(api_key=api_key),
        (*KNOWLEDGE_BASE, *source_chunks),
    )


@st.cache_data(ttl=3600, show_spinner=False)
def cached_nea_knowledge() -> tuple[str, tuple[KnowledgeChunk, ...]]:
    source_chunks = fetch_nea_sources()
    fetched_at = datetime.now().astimezone().isoformat()
    return fetched_at, source_chunks


st.set_page_config(
    page_title="Ask Clarity | ClaritySG",
    page_icon="🌫️",
    layout="wide",
)
require_password()

st.title("Ask Clarity")
st.markdown(
    "Ask about ClaritySG's PM2.5 activity guidance, PSI bands, haze, and "
    "air-quality, event-assessment, and saved-plan questions. "
    "Answers use the app's guidance plus current information retrieved from "
    "official NEA pages, with source references."
)
st.info(
    "NEA's air-pollution FAQs and haze guidance pages are fetched and cached "
    "for up to one hour. The dashboard remains the place for live readings. "
    "Today's events use 1-hour PM2.5; future events within 7 days may use "
    "24-hour PSI. Events beyond 7 days require an event-day PM2.5 recheck. "
    "Saved plans and checklist controls are current-reading tools, not forecasts "
    "or notifications. This assistant does not provide medical advice or "
    "event-cancellation decisions. Questions and retrieved excerpts are sent "
    "to OpenAI; do not include personal or sensitive information."
)
st.markdown(
    "[NEA air-pollution FAQs]"
    "(https://www.nea.gov.sg/our-services/pollution-control/air-pollution/faqs) · "
    "[NEA managing haze]"
    "(https://www.nea.gov.sg/our-services/pollution-control/air-pollution/managing-haze)"
)

suggested_questions = (
    "What does Elevated PM2.5 mean?",
    "How do 1-hour PM2.5 and 24-hour PSI differ?",
    "When should I recheck air quality for a future event?",
    "What checklist should an outdoor event prepare?",
)
st.caption("Suggested questions")
suggested_column = st.columns(len(suggested_questions))
for column, suggestion in zip(suggested_column, suggested_questions):
    if column.button(suggestion, use_container_width=True):
        st.session_state["ask_clarity_question"] = suggestion
        st.rerun()

if st.button("Refresh NEA sources now"):
    cached_nea_knowledge.clear()
    cached_knowledge_index.clear()
    st.rerun()

api_key = st.secrets.get("openai_api_key")
if not isinstance(api_key, str) or not api_key.strip():
    st.error(
        "The OpenAI API key is not configured. Add `openai_api_key` to "
        "`.streamlit/secrets.toml` or your hosting provider's secrets."
    )
    st.stop()

with st.form("ask_clarity"):
    question = st.text_area(
        "Your question",
        placeholder="What does the Elevated PM2.5 band mean?",
        max_chars=1000,
        key="ask_clarity_question",
    )
    submitted = st.form_submit_button("Ask", type="primary")

if submitted:
    if not question.strip():
        st.warning("Enter a question to continue.")
        st.stop()

    try:
        client = OpenAI(api_key=api_key.strip())
        with st.spinner("Searching the guidance and preparing an answer…"):
            fetched_at, source_chunks = cached_nea_knowledge()
            index = cached_knowledge_index(api_key.strip(), source_chunks)
            retrieved = retrieve_chunks(client, index, question.strip())
            answer = generate_answer(client, retrieved, question.strip())
    except (URLError, TimeoutError) as error:
        st.error(f"Could not retrieve current NEA source pages: {error}")
        st.stop()
    except APIError as error:
        st.error(f"Could not get an answer from OpenAI: {error}")
        st.stop()
    except ValueError as error:
        st.error(f"Could not prepare a current source-grounded answer: {error}")
        st.stop()

    fetched_time = datetime.fromisoformat(fetched_at).strftime(
        "%d %b %Y, %I:%M %p %Z"
    )
    st.caption(f"NEA source pages last fetched: {fetched_time}")
    if answer == "NOT_FOUND":
        st.info(
            "I couldn't find an answer to that in the current app and NEA "
            "sources. "
            "Check the linked official sources or rephrase the question."
        )
    else:
        source_ids = {
            int(source_id)
            for source_id in re.findall(r"\[S(\d+)\]", answer)
        }
        invalid_ids = source_ids - set(range(1, len(retrieved) + 1))
        if not source_ids or invalid_ids:
            st.error(
                "The answer did not include valid source citations, so it "
                "wasn't shown. Try asking in another way."
            )
        else:
            st.markdown(answer)
            st.subheader("Sources")
            for source_id in sorted(source_ids):
                source = retrieved[source_id - 1]
                if source.url:
                    st.markdown(f"- [{source.title}]({source.url})")
                else:
                    st.markdown(f"- {source.title} (ClaritySG methodology)")

st.caption(EDUCATIONAL_DISCLAIMER)
