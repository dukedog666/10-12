"""Team15's deliberately small Streamlit operations dashboard."""
import altair as alt
import streamlit as st

from dashboard import DATA_PATH, daily_counts, default_period, filter_period, headline_metrics, load_data, weekly_check


st.set_page_config(page_title="Team15 · Coffee Operations", page_icon="☕", layout="wide")
st.markdown("""
<style>
.block-container {max-width: 1160px; padding-top: 3.5rem; padding-bottom: 2rem;}
h1 {letter-spacing: -0.035em; font-size: 2.1rem !important;}
[data-testid="stMetric"] {background: #ffffff; border-radius: 12px;}
[data-testid="stMetricValue"] {font-variant-numeric: tabular-nums;}
</style>
""", unsafe_allow_html=True)
st.title("Coffee Sales Dashboard — Team15")
st.caption("For the vending-machine operator: prioritize drink ingredients and investigate changes in sales activity.")


@st.cache_data
def transactions(file_modified_ns):
    return load_data()


try:
    data = transactions(DATA_PATH.stat().st_mtime_ns)
except (ValueError, OSError) as exc:
    st.error(f"The transaction data could not be loaded: {exc}")
    st.stop()

source = st.selectbox("Transaction source", ["index_1", "index_2"],
                      format_func=lambda value: "Primary export · index_1" if value == "index_1" else "Secondary export · index_2",
                      key="source", help="The relationship between these exports is unconfirmed. View one at a time; do not infer a common machine or combine their trends.")
data = data.loc[data["source"].eq(source)].copy()
first_date, last_date = data["date"].min().date(), data["date"].max().date()
left, right = st.columns([1, 1.7], gap="large")
with left:
    chosen = st.date_input("Transaction period", value=default_period(data),
                           min_value=first_date, max_value=last_date, format="YYYY-MM-DD", key=f"period_{source}")
with right:
    st.caption("Default: available dates in the latest elapsed month. All metrics and charts follow the selected source and period.")
    st.caption("Historical data · Amounts use the source's units; currency has not been independently verified.")

if len(chosen) != 2:
    st.info("Choose both a start date and an end date.")
    st.stop()
start, end = chosen
if start > end:
    st.error("The start date must be on or before the end date.")
    st.stop()

selected = filter_period(data, start, end)
metrics = headline_metrics(selected)
daily = daily_counts(selected, start, end)
missing_days = daily.loc[daily["transactions"].isna(), "date"]
duplicates = int(selected.duplicated(["date", "datetime", "cash_type", "money", "coffee_name"]).sum())

c1, c2, c3 = st.columns(3)
c1.metric("Sales · source units", f"{metrics['sales']:,.2f}", border=True)
c2.metric("Transactions", f"{metrics['transactions']:,}", border=True)
c3.metric("Average transaction · source units",
          f"{metrics['average']:,.2f}" if metrics["average"] is not None else "—", border=True)

if duplicates:
    st.warning(f"{duplicates} identical extra row(s) are retained in this selection. Without transaction IDs they may be repeated exports or distinct transactions; totals and counts include them.")
if source == "index_2":
    st.caption("Secondary export starts on 8 February 2025 and has different drink coverage. It cannot establish a like-for-like performance comparison with the primary export.")

if end == last_date:
    st.caption("The final source date may be incomplete. Its recorded transactions are included above; it is excluded from the seven-day check.")
if len(missing_days):
    st.warning(f"{len(missing_days)} calendar day(s) have no records in this period. Totals describe recorded transactions only; chart gaps are not confirmed zero sales.")

check = weekly_check(data, start, end, last_date)
if check["status"] == "unavailable":
    st.info(f"Seven-day demand check unavailable. {check['reason']}")
else:
    end_label = check["cutoff"].strftime("%d %b %Y")
    text = (f"Seven-day check ending {end_label}: {check['current']} transactions vs {check['previous']} "
            f"in the preceding seven days ({check['change']:+.1%}). ")
    if check["status"] == "review":
        st.warning(text + "Review needed: check data capture, machine availability and ingredient supply. The decline does not establish the cause.")
    else:
        st.info(text + "No decline of 20% or more is flagged; this is not a statement about overall machine health.")
st.caption("The 20% decline threshold is an illustrative operating rule, not a validated fault detector.")

if selected.empty:
    st.info("No transactions were recorded in this period. Choose another date range to inspect demand.")
else:
    trend_panel, product_panel = st.columns([1.55, 1], gap="large")
    with trend_panel:
        st.subheader("When did demand change?")
        st.caption("Recorded transactions by day. Breaks indicate dates without records.")
        trend = alt.Chart(daily).mark_line(color="#885336", strokeWidth=2.5, point=True).encode(
            x=alt.X("date:T", title=None, axis=alt.Axis(format="%b %d", labelAngle=-30)),
            y=alt.Y("transactions:Q", title="Transactions", scale=alt.Scale(zero=True)),
            detail="segment:N",
            tooltip=[alt.Tooltip("date:T", title="Date", format="%Y-%m-%d"),
                     alt.Tooltip("transactions:Q", title="Transactions", format=".0f")],
        ).properties(height=300)
        st.altair_chart(trend, width="stretch")
    with product_panel:
        st.subheader("What should get priority?")
        st.caption("Demand ranking informs ingredient priorities, not exact reorder quantities.")
        products = selected.groupby("coffee_name").size().rename("transactions").reset_index()
        products = products.sort_values(["transactions", "coffee_name"], ascending=[False, True])
        if len(products) > 8:
            omitted = products.iloc[8:]
            st.caption(f"Top 8 of {len(products)} drink types. The remaining {len(omitted)} types account for {int(omitted.transactions.sum())} recorded transactions; headline totals include all types.")
        products = products.head(8)
        ranking = alt.Chart(products).mark_bar(color="#C49063", cornerRadiusEnd=3).encode(
            x=alt.X("transactions:Q", title="Transactions"),
            y=alt.Y("coffee_name:N", title=None, sort="-x", axis=alt.Axis(labelLimit=180)),
            tooltip=[alt.Tooltip("coffee_name:N", title="Drink"),
                     alt.Tooltip("transactions:Q", title="Transactions", format=".0f")],
        ).properties(height=300)
        st.altair_chart(ranking, width="stretch")

st.divider()
st.caption(f"Data: {first_date:%d %b %Y}–{last_date:%d %b %Y} · Kaggle snapshot, {source}. "
           "Intended production refresh: nightly; operator reviews exceptions daily and ingredient priorities weekly.")
with st.expander("Data notes and operating limits"):
    st.markdown("""
- Sales are recorded transaction amounts, not profit. The source currency is unverified.
- One row is treated as one transaction; no quantity field confirms cups sold.
- A date with no rows may mean no sales, closure or missing capture. It remains unknown.
- The latest day may be incomplete; the weekly check excludes it and requires two fully observed seven-day windows.
- Stock, ingredient recipes, operating hours, uptime and costs are unavailable. Exact restock quantities, stockouts and profit cannot be calculated.
- The two exports are selectable but never summed together in the dashboard; their business relationship is unconfirmed.
- Identical secondary-export rows are retained and flagged; the source lacks unique transaction IDs.
- Anonymous card identifiers are excluded from the published data. Cash transactions are retained.
""")
    st.markdown("Source: [Coffee Sales by Yaroslav Isaienkov](https://www.kaggle.com/datasets/ihelon/coffee-sales). "
                "The notebook and README document the analysis and design choices.")
