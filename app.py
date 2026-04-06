import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(
    page_title="Euroleague Assist Flow",
    page_icon="🏀",
    layout="wide"
)

TEAM_COLORS = [
    "#1D9E75", "#185FA5", "#534AB7", "#993556",
    "#BA7517", "#993C1D", "#3B6D11", "#0F6E56",
    "#0C447C", "#639922", "#E24B4A", "#D4537E"
]

# ============================================================
# LOAD DATA
# ============================================================
@st.cache_data
def load_data(file):
    df = pd.read_excel("assist_flow.xlsx")
    df = df.rename(columns={
        "PLAYER"         : "assister",
        "matched_PLAYER" : "scorer",
        "CODETEAM"       : "team",
        "Points"         : "pts"
    })
    return df

# ============================================================
# HELPERS
# ============================================================
def hex_to_rgba(hex_color, alpha=0.35):
    h = hex_color.lstrip("#")
    r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"

def evenly_spaced(n):
    if n == 1:
        return [0.5]
    return [round(i / (n - 1), 4) for i in range(n)]

# ============================================================
# SANKEY
# ============================================================
def plot_sankey(df, team, mode, round_val):
    rows = df[df["team"] == team].copy()

    if mode == "Per Round":
        rows = rows[rows["Round"] == round_val]
    else:
        rows = rows[rows["Round"] <= round_val]

    if rows.empty:
        st.warning("Δεν υπάρχουν δεδομένα για την επιλογή αυτή.")
        return None

    agg = rows.groupby(["assister", "scorer"]).size().reset_index(name="count")

    assister_totals = agg.groupby("assister")["count"].sum().sort_values(ascending=False)
    assisters = assister_totals.index.tolist()

    scorer_totals = agg.groupby("scorer")["count"].sum().sort_values(ascending=False)
    scorers = scorer_totals.index.tolist()

    a_labels = ["🏀 " + x + f" ({int(assister_totals[x])})" for x in assisters]
    s_labels = [x + f" ({int(scorer_totals[x])})" + " 🎯" for x in scorers]
    all_labels = a_labels + s_labels

    a_idx = {name: i for i, name in enumerate(assisters)}
    s_idx = {name: i + len(assisters) for i, name in enumerate(scorers)}

    sources = agg["assister"].map(a_idx).tolist()
    targets = agg["scorer"].map(s_idx).tolist()
    values  = agg["count"].tolist()

    node_colors = (
        [TEAM_COLORS[i % len(TEAM_COLORS)] for i in range(len(assisters))] +
        ["#B4B2A9"] * len(scorers)
    )
    link_colors = [hex_to_rgba(TEAM_COLORS[sources[i] % len(TEAM_COLORS)]) for i in range(len(sources))]

    node_x = [0.25] * len(assisters) + [0.75] * len(scorers)
    node_y = evenly_spaced(len(assisters)) + evenly_spaced(len(scorers))

    title = f"Assist Flow — {team} | "
    title += f"Round {round_val}" if mode == "Per Round" else f"Cumulative έως Round {round_val}"

    fig = go.Figure(go.Sankey(
        arrangement="fixed",
        node=dict(
            label=all_labels,
            color=node_colors,
            pad=20,
            thickness=25,
            line=dict(color="white", width=0.5),
            x=node_x,
            y=node_y,
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=link_colors,
            hovertemplate="<b>%{source.label}</b> → <b>%{target.label}</b><br>Assists: %{value}<extra></extra>"
        )
    ))

    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=16), x=0.5),
        font=dict(family="Arial", size=10),
        height=max(500, max(len(assisters), len(scorers)) * 60 + 100),
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(t=60, b=20, l=180, r=180)
    )

    return fig, rows, assister_totals, scorer_totals

# ============================================================
# UI
# ============================================================
st.title("🏀 Euroleague Assist Flow")
st.markdown("---")

#uploaded_file = st.file_uploader("assist_flow", type=["xlsx"])
df = load_data()

if uploaded_file:
    df = load_data(uploaded_file)

    with st.sidebar:
        st.header("Φίλτρα")

        seasons = sorted(df["Season"].unique())
        season = st.selectbox("Season", seasons, index=len(seasons)-1)

        phases = sorted(df[df["Season"] == season]["Phase"].unique())
        phase = st.selectbox("Phase", phases)

        df_filtered = df[(df["Season"] == season) & (df["Phase"] == phase)]

        teams = sorted(df_filtered["team"].unique())
        team = st.selectbox("Ομάδα", teams)

        rounds = sorted(df_filtered["Round"].unique())
        round_val = st.select_slider("Αγωνιστική", options=rounds)

        mode = st.radio("Τρόπος εμφάνισης", ["Per Round", "Cumulative"])

    result = plot_sankey(df_filtered, team, mode, round_val)

    if result:
        fig, rows, assister_totals, scorer_totals = result

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Συνολικές Assists", len(rows))
        col2.metric("Top Assister", assister_totals.index[0], f"{int(assister_totals.iloc[0])} ast")
        col3.metric("Top Scorer (από assist)", scorer_totals.index[0], f"{int(scorer_totals.iloc[0])} buckets")
        col4.metric("Παίκτες εμπλεκόμενοι", len(set(rows["assister"]) | set(rows["scorer"])))

        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Αναλυτικός πίνακας assists"):
            agg_table = rows.groupby(["assister", "scorer"]).size().reset_index(name="count")
            agg_table = agg_table.sort_values("count", ascending=False)
            st.dataframe(agg_table, use_container_width=True, hide_index=True)
        with st.expander("Top 5 ζεύγη — Ανάλυση τύπου πάσας"):
            # Top 5 ζεύγη assister→scorer
            pairs = (
                rows.groupby(["assister", "scorer"])
                .size()
                .sort_values(ascending=False)
                .head(5)
                .reset_index(name="Σύνολο")
            )
        
            # Για κάθε ζεύγος, ανάλυση ανά pts
            breakdown_rows = []
            for _, pair in pairs.iterrows():
                mask = (rows["assister"] == pair["assister"]) & (rows["scorer"] == pair["scorer"])
                pair_rows = rows[mask]
                pts_counts = pair_rows["pts"].value_counts().to_dict()
        
                breakdown_rows.append({
                    "Assister"  : pair["assister"],
                    "Scorer"    : pair["scorer"],
                    "Σύνολο"    : pair["Σύνολο"],
                    "1pt (FT)"  : int(pts_counts.get(1, 0)),
                    "2pt"       : int(pts_counts.get(2, 0)),
                    "3pt"       : int(pts_counts.get(3, 0)),
                })
        
            result_df = pd.DataFrame(breakdown_rows)
        
            # Ποσοστά
            result_df["2pt %"] = (result_df["2pt"] / result_df["Σύνολο"] * 100).round(1).astype(str) + "%"
            result_df["3pt %"] = (result_df["3pt"] / result_df["Σύνολο"] * 100).round(1).astype(str) + "%"
        
            st.dataframe(result_df, use_container_width=True, hide_index=True)

else:
    st.info("Ανέβασε το Excel αρχείο για να ξεκινήσεις.")