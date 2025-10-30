import streamlit as st


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

    # Row 1
    c1, c2, c3 = st.columns(3)
    with c1:
        card(
            label="Goal Extractor Dashboard",
            description="View quantifiable and non-quantifiable goals extracted from mastermind transcripts.",
            link_label="Goal Extractor Dashboard",
            page_path="pages/01_🎯_Goal_Extractor_Dashboard.py",
            emoji="🎯",
        )
    with c2:
        card(
            label="Vague Goals",
            description="See who has vague goals (or no goal) and why, by session date.",
            link_label="Vague Goals",
            page_path="pages/02_📝_Vague_Goals.py",
            emoji="📝",
        )
    with c3:
        card(
            label="Marketing Activity",
            description="Track marketing activities and pipeline outcomes per participant.",
            link_label="Marketing Activity",
            page_path="pages/03_📈_Marketing_Activity.py",
            emoji="📈",
        )

    st.markdown("\n")

    # Row 2
    c4, c5, c6 = st.columns(3)
    with c4:
        card(
            label="Stuck / Support Needed",
            description="Identify participants who are stuck and need support, with quotes and timestamps.",
            link_label="Stuck / Support Needed",
            page_path="pages/04_🆘_Stuck_Signals.py",
            emoji="🆘",
        )
    with c5:
        card(
            label="Challenges & Strategies",
            description="Per participant challenges, category, and actionable tips shared.",
            link_label="Challenges & Strategies",
            page_path="pages/05_🧠_Challenges_Strategies.py",
            emoji="🧠",
        )
    with c6:
        card(
            label="Member Risk Analysis",
            description="Attendance & goal achievement risk tiers with drilldowns.",
            link_label="Member Risk Analysis",
            page_path="pages/06_⚠️_Member_Risk.py",
            emoji="⚠️",
        )

    st.markdown("\n")
    # Row 3 (Pipeline)
    p1, _, _ = st.columns(3)
    with p1:
        card(
            label="Pipeline",
            description="Closed Clients, Proposals, Meetings within strict 3‑week window.",
            link_label="Pipeline",
            page_path="pages/07_📊_Pipeline.py",
            emoji="📊",
        )


if __name__ == "__main__":
    main()


