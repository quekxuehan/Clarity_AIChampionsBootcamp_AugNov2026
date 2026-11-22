import hmac

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


EDUCATIONAL_DISCLAIMER = (
    "**IMPORTANT NOTICE:** This web application is a prototype developed "
    "for **educational purposes only.** The information provided here is "
    "**NOT intended for real-world usage** and should not be relied upon "
    "for making any decisions, especially those related to financial, "
    "legal, or healthcare matters.\n\n"
    "**Furthermore, please be aware that the LLM may generate inaccurate "
    "or incorrect information. You assume full responsibility for how you "
    "use any generated output.**\n\n"
    "Always consult with qualified professionals for accurate and "
    "personalised advice."
)


def require_password() -> None:
    try:
        app_password = st.secrets["app_password"]
    except (KeyError, StreamlitSecretNotFoundError):
        st.error(
            "The app password is not configured. Add `app_password` to "
            ".streamlit/secrets.toml` or your hosting provider's secrets."
        )
        st.stop()

    if not isinstance(app_password, str) or not app_password:
        st.error("The configured app password must be a non-empty string.")
        st.stop()

    if st.session_state.get("authenticated") is True:
        with st.sidebar:
            st.caption("Navigation")
            st.page_link(
                "streamlit_app.py",
                label="ClaritySG (Home)",
                icon="🌫️",
                use_container_width=True,
            )
            st.page_link(
                "pages/1_About_Us.py",
                label="About Us",
                icon="ℹ️",
                use_container_width=True,
            )
            st.page_link(
                "pages/2_Methodology.py",
                label="Methodology",
                icon="📊",
                use_container_width=True,
            )
            st.page_link(
                "pages/3_Ask_Clarity.py",
                label="Ask Clarity",
                icon="💬",
                use_container_width=True,
            )
            if st.button("Log out", use_container_width=True):
                st.session_state["authenticated"] = False
                st.rerun()
        return

    st.title("🌫️ ClaritySG")
    st.subheader("Password required")
    st.warning(EDUCATIONAL_DISCLAIMER)
    with st.form("password_login"):
        entered_password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Unlock app")

    if submitted:
        if hmac.compare_digest(entered_password, app_password):
            st.session_state["authenticated"] = True
            st.rerun()
        st.error("Incorrect password. Try again.")

    st.stop()


def require_admin_login() -> bool:
    if st.session_state.get("is_admin") is True:
        with st.sidebar:
            if st.button("Exit admin mode", use_container_width=True):
                st.session_state["is_admin"] = False
                st.rerun()
        return True

    try:
        admin_password = st.secrets["admin_password"]
    except (KeyError, StreamlitSecretNotFoundError):
        return False

    if not isinstance(admin_password, str) or not admin_password:
        return False

    with st.sidebar.expander("Admin access", expanded=False):
        with st.form("admin_login"):
            entered_password = st.text_input(
                "Admin password",
                type="password",
                key="entered_admin_password",
            )
            submitted = st.form_submit_button("Enter admin mode")
        if submitted:
            if hmac.compare_digest(entered_password, admin_password):
                st.session_state["is_admin"] = True
                st.rerun()
            st.error("Incorrect admin password.")
    return False
