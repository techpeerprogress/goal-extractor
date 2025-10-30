import streamlit as st
import os


def card(label: str, description: str, link_label: str, page_path: str, emoji: str = "🎯"):
    """Render a simple clickable card that links to a multipage entry.

    Uses st.page_link (Streamlit >= 1.30). If unavailable, falls back to a hint.
    """
    with st.container():
        # Make the title itself the link
        try:
            st.page_link(page_path, label=f"{emoji} {label}")
        except Exception:
            # Fallback: show a note if page_link is not available
            st.markdown(f"**{emoji} {label}**")
            st.write("Use the sidebar to navigate to:", link_label)

        st.caption(description)


def main():
    st.set_page_config(page_title="Home • Goal Tools", page_icon="🏠", layout="wide")

    st.title("🏠 Home")
    st.caption("Quick access to tools and dashboards")
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        card(
            label="Goal Extractor Dashboard",
            description="View quantifiable and non-quantifiable goals extracted from mastermind transcripts.",
            link_label="Goal Extractor Dashboard",
            page_path="pages/01_🎯_Goal_Extractor_Dashboard.py",
            emoji="🎯",
        )

    # Placeholder for future cards
    with col2:
        st.markdown(
            """
            <div style="border:1px dashed #e5e7eb;border-radius:12px;padding:16px;background:#ffffff05;">
                <div style="font-size:1.1rem;font-weight:600;">Coming soon</div>
                <div style="color:#9aa2af;margin:6px 0 12px 0;">Additional dashboards and tools will appear here.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()


