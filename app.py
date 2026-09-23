"""
FIFA World Cup 2026 -- Player Performance & Scouting Dashboard (Streamlit)
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from data_pipeline import load_and_preprocess_data

# ----------------------------------------------------------------------
# PAGE CONFIG -- must be the first Streamlit call
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="FIFA World Cup 2026 - Player Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------
# DESIGN SYSTEM
# A cool, light "stadium chalk" background -- pale sage-grey, not the
# cream/gold combination used before, and nothing dark. Position colors
# are warm and saturated so they read clearly against the cool backdrop.
# ----------------------------------------------------------------------
BG = "#EAF1F6"
CARD_BG = "#FFFFFF"
INK = "#1C2622"
MUTED = "#5B6B62"
ACCENT_GREEN = "#145C43"
ACCENT_AMBER = "#B8860B"
BORDER = "#DCE3DE"

POSITION_COLORS = {
    "Forward": "#C1442D",     # brick red -- attacking
    "Midfielder": "#D1A233",  # mustard gold -- creative
    "Defender": "#1F6F63",    # teal -- solid
    "Goalkeeper": "#38415C",  # slate navy -- last line
}
POSITION_ORDER = ["Forward", "Midfielder", "Defender", "Goalkeeper"]

AXIS_LABELS = {
    "player_name": "Player Name",
    "team": "Team",
    "position": "Position",
    "goals": "Goals",
    "assists": "Assists",
    "xg_overperformance": "Goals Above Expected (xG)",
    "key_passes_per_90": "Key Passes per 90",
    "shot_conversion_pct": "Shot Conversion %",
    "defensive_actions_per_90": "Defensive Actions per 90",
    "top_speed_kmh": "Top Speed (km/h)",
    "distance_covered_km": "Distance Covered (km)",
    "total_goals": "Total Goals",
    "avg_rating": "Average Rating",
}


st.markdown(f"""
<style>
    .stApp {{ background-color: {BG}; }}
    h1, h2, h3 {{ color: {INK}; font-family: Georgia, 'Times New Roman', serif; }}
    p, li, .stMarkdown {{ color: {INK}; }}
    [data-testid="stSidebar"] {{ background-color: #D8E6EE; }}
    [data-testid="stHeader"] {{ background-color: {BG}; }}
    [data-testid="stMetricValue"] {{ color: {ACCENT_GREEN}; font-weight: 700; }}
    [data-testid="stMetricLabel"] {{ color: {MUTED}; }}
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: {CARD_BG};
        border-radius: 10px;
        border: 1px solid {BORDER} !important;
    }}
    .insight-box {{
        background-color: #F1EADA;
        border-left: 4px solid {ACCENT_AMBER};
        padding: 10px 14px;
        border-radius: 4px;
        font-size: 14.5px;
        color: {INK};
        margin-top: 6px;
    }}
    .insight-label {{
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 0.5px;
        font-weight: 700;
        color: {ACCENT_AMBER};
        margin-right: 6px;
    }}
    .headline-banner {{
        background-color: {ACCENT_GREEN};
        color: {BG};
        padding: 22px 28px;
        border-radius: 12px;
        margin-bottom: 14px;
    }}
    .headline-banner h1 {{ color: {BG}; margin: 0; }}
    .headline-banner p {{ color: #CFE0D8; margin: 4px 0 0 0; }}
    .legend-strip {{
        display: flex;
        gap: 22px;
        flex-wrap: wrap;
        background-color: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 10px 16px;
        margin-bottom: 18px;
        font-size: 13.5px;
        color: {INK};
        align-items: center;
    }}
    .legend-strip .legend-title {{
        font-weight: 700;
        color: {MUTED};
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 0.5px;
        margin-right: 6px;
    }}
    .legend-swatch {{
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 3px;
        margin-right: 6px;
        vertical-align: middle;
    }}
</style>
""", unsafe_allow_html=True)


def style_fig(fig, height=380, showlegend=True):
    fig.update_layout(
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(color=INK, family="Verdana, sans-serif", size=13),
        margin=dict(l=10, r=20, t=10, b=10),
        height=height,
        showlegend=showlegend,
        legend=dict(orientation="h", y=1.08, x=0, font=dict(size=12)),
        hoverlabel=dict(bgcolor="#FFFFFF", font_color=INK, bordercolor=BORDER),
    )
    fig.update_xaxes(gridcolor=BORDER, zeroline=False, showline=False)
    fig.update_yaxes(gridcolor=BORDER, zeroline=False, showline=False)
    return fig


def rank_desc(fig, category_order_bottom_to_top):
    """Force a horizontal-bar leaderboard to render strictly by value,
    highest at the top -- regardless of how many color groups are mixed
    in. Plotly Express otherwise clusters bars by color group first
    (e.g. all Goalkeepers together, then all Midfielders together),
    which silently breaks the ranking even when the dataframe itself
    is correctly sorted. Passing the explicit bottom-to-top category
    order removes any ambiguity."""
    fig.update_yaxes(categoryorder="array", categoryarray=category_order_bottom_to_top)
    return fig


def insight(text):
    st.markdown(
        f'<div class="insight-box"><span class="insight-label">Takeaway</span>{text}</div>',
        unsafe_allow_html=True,
    )


def position_legend():
    swatches = "".join(
        f'<span><span class="legend-swatch" style="background-color:{POSITION_COLORS[p]}"></span>{p}</span>'
        for p in POSITION_ORDER
    )
    st.markdown(
        f'<div class="legend-strip"><span class="legend-title">Color key</span>{swatches}</div>',
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------
# DATA (cached so it only loads/aggregates once per session)
# ----------------------------------------------------------------------
@st.cache_data
def get_data():
    return load_and_preprocess_data("data/fifa_world_cup_2026_player_performance.csv")

df_raw, df_players, df_teams = get_data()
TEAMS = sorted(df_players["team"].unique())
POSITIONS = sorted(df_players["position"].unique())

# ----------------------------------------------------------------------
# SIDEBAR NAVIGATION
# ----------------------------------------------------------------------
st.sidebar.markdown("### FIFA World Cup 2026")
st.sidebar.caption("Player Performance & Scouting Dashboard")
page = st.sidebar.radio(
    "Go to",
    ["Tournament Overview", "Attacking Analysis", "Defensive & Physical",
     "Team Comparison", "Head-to-Head", "Explore the Data", "About This Data"],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Position color key**")
for p in POSITION_ORDER:
    st.sidebar.markdown(
        f'<span class="legend-swatch" style="background-color:{POSITION_COLORS[p]}"></span>{p}',
        unsafe_allow_html=True,
    )

st.sidebar.markdown("---")
st.sidebar.markdown("**Filters** *(apply to every page except Team Comparison)*")
f_teams = st.sidebar.multiselect("National team", TEAMS)
f_positions = st.sidebar.multiselect("Position", POSITIONS)
f_minutes = st.sidebar.slider("Minimum minutes played", 0, int(df_players["minutes_played"].max()), 270, step=90)

d = df_players.copy()
if f_teams:
    d = d[d["team"].isin(f_teams)]
if f_positions:
    d = d[d["position"].isin(f_positions)]
d = d[d["minutes_played"] >= f_minutes]

st.sidebar.markdown("---")
st.sidebar.caption(f"Showing {len(d):,} of {len(df_players):,} players")

if d.empty:
    st.warning("No players match your current filters. Try widening them in the sidebar.")
    st.stop()

# ----------------------------------------------------------------------
# PAGE: TOURNAMENT OVERVIEW
# ----------------------------------------------------------------------
if page == "Tournament Overview":
    st.markdown(f"""
    <div class="headline-banner">
        <h1>FIFA World Cup 2026 -- Player Performance</h1>
        <p>A plain-language look at who's producing, who's creating, and who's defending across the tournament.</p>
    </div>
    """, unsafe_allow_html=True)

    position_legend()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Players tracked", f"{df_players['player_id'].nunique():,}")
    c2.metric("Teams", f"{len(TEAMS)}")
    c3.metric("Goals scored", f"{int(df_players['goals'].sum()):,}")
    c4.metric("Avg. pass accuracy", f"{df_players['pass_accuracy_pct'].mean():.0f}%")

    st.write("")
    left, right = st.columns(2)

    with left:
        with st.container(border=True):
            st.markdown("##### Top 10 Goal Scorers")
            top10 = d.nlargest(10, "goals").sort_values("goals")
            fig = px.bar(top10, x="goals", y="player_name", orientation="h", text="goals",
                         color="position", color_discrete_map=POSITION_COLORS, labels=AXIS_LABELS)
            fig.update_traces(textposition="outside", cliponaxis=False)
            st.plotly_chart(rank_desc(style_fig(fig, showlegend=False), top10["player_name"].tolist()), width='stretch')
            top = top10.iloc[-1]
            insight(f"<b>{top['player_name']}</b> ({top['team']}) tops the charts with <b>{int(top['goals'])} goals</b> -- "
                    f"the tournament's most direct goal threat so far.")

    with right:
        with st.container(border=True):
            st.markdown("##### Top 10 Assist Providers")
            top10a = d.nlargest(10, "assists").sort_values("assists")
            fig = px.bar(top10a, x="assists", y="player_name", orientation="h", text="assists",
                         color="position", color_discrete_map=POSITION_COLORS, labels=AXIS_LABELS)
            fig.update_traces(textposition="outside", cliponaxis=False)
            st.plotly_chart(rank_desc(style_fig(fig, showlegend=False), top10a["player_name"].tolist()), width='stretch')
            topa = top10a.iloc[-1]
            insight(f"<b>{topa['player_name']}</b> ({topa['team']}) leads all creators with <b>{int(topa['assists'])} assists</b> -- "
                    f"the tournament's top provider for teammates.")

    st.write("")
    with st.container(border=True):
        st.markdown("##### Goals Scored, by Position")
        pos_goals = d.groupby("position", as_index=False)["goals"].sum().sort_values("goals")
        fig = px.bar(pos_goals, x="goals", y="position", orientation="h", text="goals",
                     color="position", color_discrete_map=POSITION_COLORS, labels=AXIS_LABELS)
        fig.update_traces(textposition="outside", cliponaxis=False)
        st.plotly_chart(rank_desc(style_fig(fig, height=260, showlegend=False), pos_goals["position"].tolist()), width='stretch')
        top_pos = pos_goals.iloc[-1]
        insight(f"<b>{top_pos['position']}s</b> have scored the most goals overall ({int(top_pos['goals'])}) -- "
                f"consistent with how real football works, which is a good sign this dataset behaves sensibly.")

# ----------------------------------------------------------------------
# PAGE: ATTACKING ANALYSIS
# ----------------------------------------------------------------------
elif page == "Attacking Analysis":
    st.markdown("## Attacking Analysis")
    st.caption("Who finishes clinically, and who creates the most danger -- explained without jargon.")

    with st.expander("What does 'xG' mean? (10-second explainer)"):
        st.write(
            "Expected Goals (xG) estimates how likely a shot was to result in a goal, based on things like "
            "distance and angle. A player who scores more goals than their xG suggests is finishing clinically -- "
            "getting more out of their chances than an average player would. A player scoring fewer is missing "
            "chances a typical player would convert."
        )

    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.markdown("##### Most Clinical Finishers")
            st.caption("Goals scored above what their shot quality (xG) predicted")
            clinical = d[d["minutes_played"] >= 270].nlargest(10, "xg_overperformance").sort_values("xg_overperformance")
            fig = px.bar(clinical, x="xg_overperformance", y="player_name", orientation="h",
                         text="xg_overperformance", color="position", color_discrete_map=POSITION_COLORS, labels=AXIS_LABELS)
            fig.update_traces(textposition="outside", cliponaxis=False, texttemplate="+%{text:.1f}")
            st.plotly_chart(rank_desc(style_fig(fig, showlegend=False), clinical["player_name"].tolist()), width='stretch')
            if not clinical.empty:
                top = clinical.iloc[-1]
                insight(f"<b>{top['player_name']}</b> scored <b>{top['xg_overperformance']:.1f} goals more</b> than their "
                        f"chances suggested they should -- a sign of clinical, high-quality finishing.")

    with right:
        with st.container(border=True):
            st.markdown("##### Biggest Creators")
            st.caption("Key passes per 90 minutes -- chances set up for teammates, adjusted for playing time")
            creators = d.nlargest(10, "key_passes_per_90").sort_values("key_passes_per_90")
            fig = px.bar(creators, x="key_passes_per_90", y="player_name", orientation="h",
                         text="key_passes_per_90", color="position", color_discrete_map=POSITION_COLORS, labels=AXIS_LABELS)
            fig.update_traces(textposition="outside", cliponaxis=False)
            st.plotly_chart(rank_desc(style_fig(fig, showlegend=False), creators["player_name"].tolist()), width='stretch')
            if not creators.empty:
                top = creators.iloc[-1]
                insight(f"<b>{top['player_name']}</b> creates <b>{top['key_passes_per_90']:.1f} key passes every 90 minutes</b> -- "
                        f"the tournament's most reliable chance-creator relative to time on the pitch.")

    st.write("")
    with st.container(border=True):
        st.markdown("##### Shot Conversion Leaders")
        st.caption("Of every 100 shots a player takes, how many go in? (Minimum 8 shots, so one lucky strike can't skew the picture)")
        conv = d[d["shots"] >= 8].nlargest(10, "shot_conversion_pct").sort_values("shot_conversion_pct")
        fig = px.bar(conv, x="shot_conversion_pct", y="player_name", orientation="h", text="shot_conversion_pct",
                     color="position", color_discrete_map=POSITION_COLORS, labels=AXIS_LABELS)
        fig.update_traces(textposition="outside", cliponaxis=False, texttemplate="%{text:.0f}%")
        st.plotly_chart(rank_desc(style_fig(fig, showlegend=False), conv["player_name"].tolist()), width='stretch')
        if not conv.empty:
            top = conv.iloc[-1]
            insight(f"<b>{top['player_name']}</b> converts <b>{top['shot_conversion_pct']:.0f}% of shots</b> into goals -- "
                    f"the most efficient finisher among players with at least 8 shots.")

# ----------------------------------------------------------------------
# PAGE: DEFENSIVE & PHYSICAL
# ----------------------------------------------------------------------
elif page == "Defensive & Physical":
    st.markdown("## Defensive & Physical Performance")
    st.caption("Who does the unglamorous work -- winning the ball back and covering the ground.")

    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.markdown("##### Top Defenders by Actions")
            st.caption("Tackles + interceptions + clearances + blocks, per 90 minutes")
            top_def = d.nlargest(10, "defensive_actions_per_90").sort_values("defensive_actions_per_90")
            fig = px.bar(top_def, x="defensive_actions_per_90", y="player_name", orientation="h",
                         text="defensive_actions_per_90", color="position", color_discrete_map=POSITION_COLORS, labels=AXIS_LABELS)
            fig.update_traces(textposition="outside", cliponaxis=False)
            st.plotly_chart(rank_desc(style_fig(fig, showlegend=False), top_def["player_name"].tolist()), width='stretch')
            if not top_def.empty:
                top = top_def.iloc[-1]
                insight(f"<b>{top['player_name']}</b> ({top['position']}) makes <b>{top['defensive_actions_per_90']:.1f} "
                        f"defensive actions every 90 minutes</b> -- the busiest defender relative to time played.")

    with right:
        with st.container(border=True):
            st.markdown("##### Fastest Players")
            st.caption("Top recorded sprint speed (km/h)")
            fastest = d.nlargest(10, "top_speed_kmh").sort_values("top_speed_kmh")
            fig = px.bar(fastest, x="top_speed_kmh", y="player_name", orientation="h", text="top_speed_kmh",
                         color="position", color_discrete_map=POSITION_COLORS, labels=AXIS_LABELS)
            fig.update_traces(textposition="outside", cliponaxis=False, texttemplate="%{text:.1f}")
            st.plotly_chart(rank_desc(style_fig(fig, showlegend=False), fastest["player_name"].tolist()), width='stretch')
            if not fastest.empty:
                top = fastest.iloc[-1]
                insight(f"<b>{top['player_name']}</b> hit a top speed of <b>{top['top_speed_kmh']:.1f} km/h</b> -- "
                        f"the quickest player in the current selection.")

    st.write("")
    with st.container(border=True):
        st.markdown("##### Average Distance Covered per Match, by Position")
        st.caption("A simple, honest comparison -- no statistics background needed")
        dist_by_pos = d.groupby("position", as_index=False)["distance_covered_km"].mean().sort_values("distance_covered_km")
        fig = px.bar(dist_by_pos, x="distance_covered_km", y="position", orientation="h",
                     text="distance_covered_km", color="position", color_discrete_map=POSITION_COLORS, labels=AXIS_LABELS)
        fig.update_traces(textposition="outside", cliponaxis=False, texttemplate="%{text:.1f} km")
        st.plotly_chart(rank_desc(style_fig(fig, height=260, showlegend=False), dist_by_pos["position"].tolist()), width='stretch')
        top_runner = dist_by_pos.iloc[-1]
        insight(f"<b>{top_runner['position']}s</b> cover the most ground per match on average "
                f"({top_runner['distance_covered_km']:.1f} km) -- consistent with their box-to-box role connecting defense and attack.")

# ----------------------------------------------------------------------
# PAGE: TEAM COMPARISON
# ----------------------------------------------------------------------
elif page == "Team Comparison":
    st.markdown("## Team Comparison")
    st.caption("Compare up to 6 national teams side by side on the metrics that matter most.")

    default_teams = df_teams.nlargest(4, "total_goals")["team"].tolist()
    chosen = st.multiselect("Choose teams to compare", TEAMS, default=default_teams, max_selections=6)

    if not chosen:
        st.info("Pick at least one team above to see the comparison.")
    else:
        t = df_teams[df_teams["team"].isin(chosen)]

        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.markdown("##### Total Goals Scored")
                t_goals = t.sort_values("total_goals")
                fig = px.bar(t_goals, x="total_goals", y="team", orientation="h", text="total_goals",
                             color_discrete_sequence=[ACCENT_GREEN], labels=AXIS_LABELS)
                fig.update_traces(textposition="outside", cliponaxis=False)
                st.plotly_chart(rank_desc(style_fig(fig, height=280, showlegend=False), t_goals["team"].tolist()), width='stretch')

        with c2:
            with st.container(border=True):
                st.markdown("##### Average Player Rating")
                t_rating = t.sort_values("avg_rating")
                fig = px.bar(t_rating, x="avg_rating", y="team", orientation="h", text="avg_rating",
                             color_discrete_sequence=[ACCENT_AMBER], labels=AXIS_LABELS)
                fig.update_traces(textposition="outside", cliponaxis=False, texttemplate="%{text:.1f}")
                st.plotly_chart(rank_desc(style_fig(fig, height=280, showlegend=False), t_rating["team"].tolist()), width='stretch')

        with st.container(border=True):
            st.markdown("##### Head-to-Head Table")
            show_cols = ["team", "squad_size", "total_goals", "total_assists", "total_xg",
                         "avg_pass_accuracy", "avg_rating", "total_yellow_cards", "total_red_cards"]
            nice_names = {"team": "Team", "squad_size": "Squad Size", "total_goals": "Goals",
                          "total_assists": "Assists", "total_xg": "Total xG",
                          "avg_pass_accuracy": "Avg Pass Acc %", "avg_rating": "Avg Rating",
                          "total_yellow_cards": "Yellow Cards", "total_red_cards": "Red Cards"}
            st.dataframe(t[show_cols].rename(columns=nice_names).sort_values("Goals", ascending=False),
                         width='stretch', hide_index=True)

# ----------------------------------------------------------------------
# PAGE: HEAD-TO-HEAD PLAYER COMPARISON
# ----------------------------------------------------------------------
elif page == "Head-to-Head":
    st.markdown("## Head-to-Head Player Comparison")
    st.caption("Pick any two players and compare them across six key metrics -- no stats knowledge required.")

    options = d.apply(lambda r: f"{r['player_name']} ({r['team']}, {r['position']})", axis=1)
    label_to_id = dict(zip(options, d["player_id"]))
    labels = sorted(options)

    c1, c2 = st.columns(2)
    p1_label = c1.selectbox("Player A", labels, index=0 if labels else None)
    p2_label = c2.selectbox("Player B", labels, index=min(1, len(labels) - 1) if labels else None)

    if p1_label and p2_label:
        p1 = df_players[df_players["player_id"] == label_to_id[p1_label]].iloc[0]
        p2 = df_players[df_players["player_id"] == label_to_id[p2_label]].iloc[0]

        categories = ["Goals/90", "Assists/90", "Key Passes/90", "Defensive Actions/90", "Pass Accuracy %", "Rating (x10)"]

        def metrics_for(r):
            return [r["goals_per_90"], r["assists_per_90"], r["key_passes_per_90"],
                    r["defensive_actions_per_90"], r["pass_accuracy_pct"] / 10, r["player_rating"]]

        with st.container(border=True):
            st.markdown("##### Visual Comparison")
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=metrics_for(p1), theta=categories, fill="toself",
                                           name=f"{p1['player_name']}", line_color=ACCENT_GREEN, opacity=0.75))
            fig.add_trace(go.Scatterpolar(r=metrics_for(p2), theta=categories, fill="toself",
                                           name=f"{p2['player_name']}", line_color=ACCENT_AMBER, opacity=0.75))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10], gridcolor=BORDER),
                                          angularaxis=dict(gridcolor=BORDER), bgcolor=BG))
            st.plotly_chart(style_fig(fig, height=430), width='stretch')

        with st.container(border=True):
            st.markdown("##### The Raw Numbers, Side by Side")
            compare_cols = ["goals", "assists", "expected_goals_xg", "pass_accuracy_pct",
                            "defensive_actions_per_90", "distance_covered_km", "player_rating"]
            nice = {"goals": "Goals", "assists": "Assists", "expected_goals_xg": "Expected Goals (xG)",
                    "pass_accuracy_pct": "Pass Accuracy %", "defensive_actions_per_90": "Defensive Actions / 90",
                    "distance_covered_km": "Distance Covered (km/match)", "player_rating": "Average Rating"}
            table = pd.DataFrame({
                "Metric": [nice[c] for c in compare_cols],
                p1["player_name"]: [p1[c] for c in compare_cols],
                p2["player_name"]: [p2[c] for c in compare_cols],
            })
            st.dataframe(table, width='stretch', hide_index=True)

# ----------------------------------------------------------------------
# PAGE: EXPLORE THE DATA
# ----------------------------------------------------------------------
elif page == "Explore the Data":
    st.markdown("## Explore the Full Dataset")
    st.caption("Every player's tournament summary. Click a column header to sort; use the sidebar filters to narrow it down.")

    show_cols = ["player_name", "team", "position", "age", "matches_played", "minutes_played",
                 "goals", "assists", "expected_goals_xg", "pass_accuracy_pct",
                 "defensive_actions_per_90", "distance_covered_km", "player_rating", "scouting_score"]
    nice = {c: c.replace("_", " ").title() for c in show_cols}
    display_df = d[show_cols].rename(columns=nice).sort_values("Goals", ascending=False)

    st.dataframe(display_df, width='stretch', hide_index=True, height=520)

    csv = display_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download this table as CSV", csv, "fifa_2026_player_summary.csv", "text/csv")

# ----------------------------------------------------------------------
# PAGE: ABOUT THIS DATA
# ----------------------------------------------------------------------
elif page == "About This Data":
    st.markdown("## About This Dashboard")

    with st.container(border=True):
        st.markdown("##### What this is")
        st.write(
            "This dashboard summarizes 54,600 match-level player records (1,248 players, 48 teams) from a "
            "FIFA World Cup 2026 dataset into a clean, one-row-per-player tournament summary, then presents "
            "it as simple leaderboards and comparisons."
        )

    with st.container(border=True):
        st.markdown("##### Important limitation -- please read before sharing")
        st.write(
            "This is a synthetic, generated dataset (from Kaggle), not official FIFA data. Some players show "
            "far more \"matches played\" than a real World Cup allows (a real tournament caps out around 7-8 "
            "games per team; this data shows up to 60+ for some players), because of how the dataset was "
            "generated -- not because of an error in this dashboard. The methodology applied here (per-90 "
            "normalization, xG comparisons, etc.) is standard and sound; the underlying numbers are simulated. "
            "Be upfront about that if you present or publish this."
        )

    with st.container(border=True):
        st.markdown("##### How the numbers are calculated")
        st.write(
            "- Per-90 metrics (e.g. Goals/90) = a player's total for that stat divided by (total minutes played / 90). "
            "This puts players who played different amounts of time on a level footing.\n"
            "- xG overperformance = actual goals scored minus expected goals (xG). Positive means a player is "
            "finishing better than their shot quality alone would predict.\n"
            "- Pass accuracy % = successful passes divided by total passes, times 100.\n"
            "- Scouting score (visible in the Explore page) is a transparent, custom 0-100 index -- "
            "goalkeepers are scored mainly on save percentage and clean sheets; outfield players on a blend of "
            "goals, assists, xG, defensive work, passing, and match rating. It's a documented starting point for "
            "discussion, not a claim of objective truth."
        )

    with st.container(border=True):
        st.markdown("##### Tech stack")
        st.write("Python, Pandas, Streamlit, Plotly")
