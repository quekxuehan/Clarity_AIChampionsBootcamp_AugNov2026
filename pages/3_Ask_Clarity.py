import re

import streamlit as st
from openai import APIError, OpenAI

from app_common import EDUCATIONAL_DISCLAIMER, require_password
from rag import (
    KnowledgeIndex,
    build_knowledge_index,
    generate_answer,
    retrieve_chunks,
)


@st.cache_resource(show_spinner=False)
def cached_knowledge_index(api_key: str) -> KnowledgeIndex:
    return build_knowledge_index(OpenAI(api_key=api_key))


st.set_page_config(
    page_title="Ask Clarity | Clarity SG",
    page_icon="🌫️",
    layout="wide",
)
require_password()

st.title("Ask Clarity")
st.markdown(
    "Ask about Clarity SG's PM2.5 activity guidance, PSI bands, and data "
    "sources. Answers are generated from the app's knowledge base and include "
    "source references."
)
st.info(
    "This assistant explains the app's guidance; it does not provide live "
    "readings, forecasts, medical advice, or event-cancellation decisions. "
    "Questions are sent to OpenAI to generate embeddings and answers. Do not "
    "include personal or sensitive information."
)

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
    )
    submitted = st.form_submit_button("Ask", type="primary")

if submitted:
    if not question.strip():
        st.warning("Enter a question to continue.")
        st.stop()

    try:
        client = OpenAI(api_key=api_key.strip())
        with st.spinner("Searching the guidance and preparing an answer…"):
            index = cached_knowledge_index(api_key.strip())
            retrieved = retrieve_chunks(client, index, question.strip())
            answer = generate_answer(client, retrieved, question.strip())
    except APIError as error:
        st.error(f"Could not get an answer from OpenAI: {error}")
        st.stop()
    except ValueError as error:
        st.error(f"Could not prepare a source-grounded answer: {error}")
        st.stop()

    if answer == "NOT_FOUND":
        st.info(
            "I couldn't find an answer to that in the current knowledge base. "
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
                    st.markdown(f"- {source.title} (Clarity SG methodology)")

st.caption(EDUCATIONAL_DISCLAIMER)
