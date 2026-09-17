import streamlit as st

from independent.app.data import PROVINCES, TIER_COLOR, TIER_LABEL, schools_2025

df = schools_2025()

st.title("2025 risk list")
st.caption("Ranked worst first. Lower score = higher risk of losing learners faster than the province "
           "over 2025–2027. Select a row to open the school's profile.")

with st.container(border=True):
    with st.container(horizontal=True, vertical_alignment="bottom"):
        provinces = st.multiselect(
            "Province", sorted(df.province.unique()), format_func=lambda p: PROVINCES[p],
            placeholder="All provinces", key="rl_provinces")
        pool = df[df.province.isin(provinces)] if provinces else df
        districts = st.multiselect(
            "District", sorted(pool.district.dropna().unique()), format_func=str.title,
            placeholder="All districts", key="rl_districts")
        search = st.text_input("School name or EMIS", placeholder="e.g. Sinugani", key="rl_search")
    with st.container(horizontal=True, vertical_alignment="bottom"):
        tiers = st.pills("Tier", ["PRIORITY", "WATCH", ""], selection_mode="multi",
                         default=["PRIORITY", "WATCH"], format_func=TIER_LABEL.get, key="rl_tiers")
        sectors = st.pills("Sector", ["PUBLIC", "INDEPENDENT"], selection_mode="multi",
                           default=["PUBLIC", "INDEPENDENT"], format_func=str.title, key="rl_sectors")
        quint = st.pills("Quintile", [1, 2, 3, 4, 5], selection_mode="multi",
                         format_func=lambda q: f"Q{q}", key="rl_quint")

view = df
if provinces:
    view = view[view.province.isin(provinces)]
if districts:
    view = view[view.district.isin(districts)]
if tiers:
    view = view[view.tier.isin(tiers)]
if sectors:
    view = view[view.sector.isin(sectors)]
if quint:
    view = view[view.quintile.isin(quint)]
if search:
    s = search.strip()
    view = view[view.school.str.contains(s, case=False, na=False) | view.emis.astype(str).str.contains(s)]

with st.container(horizontal=True):
    st.metric("Schools shown", f"{len(view):,}", border=True)
    st.metric("Priority", f"{(view.tier == 'PRIORITY').sum():,}", border=True)
    st.metric("Watch", f"{(view.tier == 'WATCH').sum():,}", border=True)
    st.metric("Learners in these schools", f"{view.learners.sum():,.0f}", border=True)

if view.empty:
    st.info("No schools match these filters.", icon=":material/filter_alt_off:")
    st.stop()

map_col, table_col = st.columns([2, 3])
with map_col.container(border=True):
    st.markdown("**Where they are**")
    # Draw lower-risk first and priority last, so the schools that matter sit on top.
    order = {"": 0, "WATCH": 1, "PRIORITY": 2}
    pts = (view.dropna(subset=["lat", "lon"]).assign(color=lambda d: d.tier.map(TIER_COLOR))
           .sort_values("tier", key=lambda t: t.map(order)))
    st.map(pts, latitude="lat", longitude="lon", color="color", size=700, height=520)
    st.caption(f":red[●] Priority · :yellow[●] Watch · :blue[●] Lower risk · "
               f"{len(view) - len(pts)} shown schools have no location on record")

with table_col.container(border=True):
    st.markdown("**The list**")
    table = view[["rank", "emis", "school", "district", "province", "learners", "quintile", "score",
                  "p_loss", "tier_label", "reason_1", "reason_2", "reason_3"]].reset_index(drop=True)
    event = st.dataframe(
        table, hide_index=True, height=520, on_select="rerun", selection_mode="single-row",
        key="rl_table",
        column_config={
            "rank": st.column_config.NumberColumn("Rank", width="small", pinned=True),
            "emis": st.column_config.NumberColumn("EMIS", format="%d"),
            "school": st.column_config.TextColumn("School", pinned=True),
            "district": "District",
            "province": st.column_config.TextColumn("Prov.", width="small"),
            "learners": st.column_config.NumberColumn("Learners", format="%d"),
            "quintile": st.column_config.NumberColumn("Q", format="%d", width="small"),
            "score": st.column_config.NumberColumn("Score", help="Lower = higher risk", format="%d"),
            "p_loss": st.column_config.ProgressColumn(
                "P(loss)", format="percent", min_value=0, max_value=0.4,
                help="Modelled probability of losing learners faster than the province by 2027"),
            "tier_label": "Tier",
            "reason_1": "Top reason",
            "reason_2": "Second reason",
            "reason_3": "Third reason",
        },
    )
    rows = event.selection.rows
    with st.container(horizontal=True, vertical_alignment="center"):
        if rows:
            chosen = table.iloc[rows[0]]
            st.session_state.emis = int(chosen.emis)
            if st.button(f"Open profile: {chosen.school.title()}", icon=":material/school:", type="primary"):
                st.switch_page("app_pages/school.py")
        else:
            st.caption("Select a row to open its profile.")
        st.download_button(
            "Download this list (CSV)", table.to_csv(index=False).encode("utf-8"),
            file_name="learner_loss_risk_2025.csv", mime="text/csv", icon=":material/download:")
