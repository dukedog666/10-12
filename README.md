# Coffee Sales Operations Dashboard — Team15

A small Streamlit dashboard for a coffee vending-machine operator who needs to prioritize ingredient preparation and investigate changes in transaction activity. This is a historical demonstration, not a live sales monitor.

**Public repository:** https://github.com/dukedog666/10-12 . **Cloud app:** pending deployment; see `DEPLOYMENT.md`. Local validation evidence is in `VALIDATION.md`, and a Chinese walkthrough is in `项目思路说明.md`.

## Step 1 — Dataset and decision-maker

**Dataset:** [Coffee Sales by Yaroslav Isaienkov](https://www.kaggle.com/datasets/ihelon/coffee-sales). The author describes it as transaction data from a vending machine they operate. We treat it as author-reported real operational data, not independently verified business records. [Author introduction](https://www.kaggle.com/getting-started/521180).

The decision-maker is **the operator responsible for ingredient replenishment and machine checks**. This is a proposed business persona; we have not interviewed the actual operator.

We retain both supplied exports with explicit source tags. The default view uses `index_1.csv`, covering **1 March 2024–23 March 2025**, with **3,636 records** and **8 drink categories**. One row represents a recorded transaction. No quantity column confirms cups sold, and repeated customers may make multiple transactions. Prices are reported in **source units** because the supplied files do not identify the currency reliably.

The second file has **262 rows**, **30 drink categories** and **8 February–23 March 2025** coverage. It lacks the anonymous card identifier and contains two identical extra rows. It overlaps the primary file's dates but has no matching transaction after timestamp and drink-name normalization. This does not establish whether it is another machine, location or scope. We provide a **source selector**, never an all-sources total or combined trend. The selector identifies exports, not verified machines or locations. No cross-source performance claim is made.

### Preparation and provenance

- Publish one small CSV, `data/coffee_sales.csv`, containing both exports with a `source` column. It has **3,898 recorded rows**, approximately **254 KB**, well below 25 MB. Collecting rows into one file does not authorize treating the sources as one business trend.
- Keep all 3,636 primary records; its required time, drink, payment and amount fields are complete, its dates agree with timestamps, all amounts are positive, and it has no fully duplicate rows.
- Remove the anonymous `card` identifier; it is unnecessary for this decision. The 89 missing card identifiers are all cash payments, so **none of these cash transactions is discarded**.
- Trim drink-name whitespace and sort timestamps. Do not merge distinct names speculatively.
- Retain all 262 secondary rows, including two identical extra rows on 2025-02-26 and 2025-03-23. Without a unique transaction ID these might be repeated exports or distinct transactions within the same second; the app flags them and explains that totals include them.
- Do not fill dates without records with zero or impute transactions. The seven primary dates are 2024-05-01, 2024-05-04, 2024-05-05, 2024-11-27, 2025-01-01, 2025-01-19 and 2025-01-23. The three secondary dates are 2025-03-04, 2025-03-06 and 2025-03-13.
- `data/source_audit.json` records source hashes, sizes, coverage, missing values and selection decisions without publishing card values.

`scripts/prepare_data.py` reproduces the published CSV from the two downloaded source files; neither original file is redistributed unchanged. Kaggle's public metadata inspected for this project reports **CC0: Public Domain**. We still credit the author and link to the source.

## Step 2 — Why a dashboard?

### Who looks at it, and how often?

The operator reviews exceptions daily and reviews drink demand weekly before scheduling ingredient purchases and visits.

### What decision does it support?

**If the operator sees a drink consistently account for a large share of recent transactions, they will prioritize its ingredients during the next replenishment plan. If they see a material decrease in seven-day transaction activity, they will first verify data capture and then inspect machine availability and ingredient supply.**

The ranking is a planning cue. It is not a reorder calculator: recipes, ingredient quantities, stock on hand, delivery lead times and spoilage data are absent.

### What happens without it?

Our scenario assumes the operator currently opens exported transaction files, chooses dates and manually summarizes drink demand. Repeating those steps creates avoidable work and makes inconsistently chosen periods or missed declines more likely. We do not claim a measured number of hours saved, a financial return or an observed current workflow.

### Why not a weekly email, report or alert?

A weekly email would be sufficient for a fixed summary. The dashboard earns its place when this same operator needs to inspect an unusual period, compare the shape of demand over dates and examine the drink mix before changing a replenishment plan. A date filter enables that repeated investigation. A single decline alert can prompt a check but cannot show whether activity changed briefly or throughout the period, nor which drinks dominate demand. The dashboard supports the follow-up; an alert would complement it in production.

For a one-off analysis of this frozen historical snapshot, a report would be the simpler choice. This course app is a prototype for the proposed recurring workflow, not evidence that the actual vending business needs a dashboard. If the real operator only reads a fixed weekly summary and does not investigate periods interactively, a weekly report should replace the dashboard.

## Step 3 — EDA, what matters, and page order

`eda.ipynb` is an executed, reproducible Pandas and Matplotlib notebook. It documents shape, types, missingness, distributions, data relationships, source separation and limitations. It reads the same prepared CSV as the app, inspects both source audits, and uses the primary source for the longer time-pattern analysis.

### Findings used in the design

- Primary-source all-period recorded sales are **115,431.58 source units** across **3,636 transactions**, averaging **31.75 per transaction**. The secondary source has **6,890.00 source units**, **262 rows** and a **26.30** average, including the unresolved duplicate rows. These are separate reconciliation totals, not today's performance or like-for-like source comparisons.
- Americano with Milk has **824 transactions**, Latte **782**, and Americano **578**. Latte has higher recorded revenue than Americano with Milk despite fewer transactions. Therefore revenue rank is not an adequate proxy for ingredient demand.
- Each drink has multiple recorded prices (five or six distinct amounts). Revenue changes can reflect price or mix changes as well as transaction activity. We avoid attributing every revenue movement to demand.
- Seven primary dates and three secondary dates lack records; reasons are unknown. They are chart gaps, not confirmed zero-sales days.
- The final source date stops at a particular transaction timestamp and has no closing or completeness marker. We exclude it from the seven-day comparison, while retaining its recorded transactions in period totals.
- February 2025 is the latest fully elapsed calendar month and the primary source has records on all 28 days. It is the primary default filter, rather than the partly covered final month. The secondary default covers **8–28 February**, its available dates in that month; this is explicitly a partial month and not a comparable monthly total.

### At most three headline numbers

| KPI | Definition | Decision relevance |
| --- | --- | --- |
| Sales | Sum of recorded `money` in the selected period | Scale of recorded business activity |
| Transactions | Number of rows in the selected period | Demand volume without price-driven changes |
| Average transaction | Sales divided by transactions | Context for interpreting revenue and mix |

All values use the same selected source and inclusive transaction-date filter. Empty periods show zero recorded sales, zero records and an unavailable average (`—`), together with a no-records message; this is not a claim of verified zero actual sales. We deliberately omit KPI deltas: arbitrary date selections may have different lengths, weekday mixes and source coverage.

### Two supporting charts and two necessary filters

1. **Daily transaction trend:** explains whether recorded demand changed suddenly or gradually. The chart uses a complete calendar index and separate line segments around no-record dates; it never joins across a gap to conceal uncertainty.
2. **Drink transaction ranking:** identifies demand priorities. It uses transaction counts rather than revenue and displays at most eight categories to keep the page readable. When additional secondary categories exist, a caption states how many categories and transactions are outside the chart. Headline totals always include all categories; the source file remains available for a detailed review.

The filters are **source export** and an inclusive **transaction date range**. The source filter is necessary to prevent an unsupported aggregate, and switching it changes available dates and the default period. The operator needs to inspect a relevant period; the data cannot support a verified machine or location selector, and selecting drinks individually would hide the mix needed for ingredient planning. The proposed persona assumes one operator is responsible for reviewing these provided exports; their actual business relationship remains unknown.

### What we chose not to show

- **Payment-method pie chart:** an interesting EDA breakdown, but this operator's ingredient and machine-check decisions do not depend on it.
- **Anonymous card/customer leaderboard:** not needed for replenishment, and transaction identifiers do not establish unique people. Card identifiers are excluded from the published CSV.
- **Profit, stockout and reorder metrics:** no costs, inventory or recipes exist. Fabricating them would imply decisions the data cannot support.
- **Raw transaction table:** this task is aggregate planning, not payment reconciliation. Neither a table nor extra charts justify the page space.

### Top-to-bottom sketch and rationale

```text
Title: Coffee Sales Dashboard — Team15
One-line caption identifying the operator and decision
Source export + date range + historical-snapshot context
Sales | Transactions | Average transaction
Coverage notice if needed + one short seven-day check
Daily transaction trend | Drink transaction ranking
Data period + intended refresh/review frequency
Collapsed source notes and limitations
```

The date selector is near the top so the meaning of every number is immediately clear. The three KPIs precede the explanatory charts. The exception check supplies an action cue without adding a fourth KPI or a third chart. Source notes are collapsed at the bottom to keep the first screen focused; material coverage and currency cautions remain visible.

## Step 4 — Refresh, review and action

### Refresh and review are different

In production, load transaction data **nightly**, after the previous day's sales are complete. The operator checks exceptions daily and uses the dashboard **weekly** to prioritize ingredients. Minute-by-minute refresh would not materially improve a weekly replenishment plan and would add ingestion and monitoring cost. Actual machine failure notifications or stock sensors would be separate real-time alerts if available.

This submitted app uses a frozen Kaggle snapshot and has no live ingestion or scheduled refresh. The footer states its data period and the intended production cadence. Cache behavior does not turn a static file into new data.

### One metric that triggers a check

Monitor **seven-day transaction count**. An illustrative decline of **20% or more** versus the previous seven days prompts a review of capture completeness, machine availability and ingredients. Use two consecutive seven-day periods to keep the weekday mix comparable. This threshold is a design proposal, not a demonstrated fault boundary, and should be tuned using operational history and the cost of unnecessary visits.

The app computes this check only when both windows lie inside the selected date range and every calendar day in both has at least one record. A no-record day is unresolved and suppresses the decline conclusion. This is conservative: a real zero-sales day cannot be distinguished from missing capture. The final source date is excluded because its complete-day coverage is unverified. No-record periods require data review rather than an invented zero.

For the default February 2025 filter, the comparison is 22–28 February (**99 transactions**) against 15–21 February (**119 transactions**): **−16.8%**, which does not trigger the proposed 20% decline rule. That result does not prove the machine is healthy or ingredients are available.

### What stale data costs

A one-day delay may postpone investigating an unusual decline; a week-old snapshot may cause ingredient priorities to reflect an obsolete drink mix, leading to unnecessary stock or overlooked demand. These are plausible operational consequences, not measured losses. Production should display the most recent completed ingestion timestamp and flag freshness problems separately from low sales.

## Step 5 — Run, verify and deploy

The project was initialized with `uv init`. Python **3.14** is specified in `.python-version` and the project configuration, matching the assignment.

```bash
uv sync
uv run streamlit run app.py
```

To rerun the notebook and app checks:

```bash
uv sync --group dev
uv run python scripts/build_notebook.py
uv run python -m unittest discover -s tests -v
```

To reproduce preparation from your original downloads:

```bash
uv run python scripts/prepare_data.py --primary /path/to/index_1.csv --secondary /path/to/index_2.csv
```

### Streamlit Community Cloud settings

1. Publish these project files at the root of your own **public GitHub repository**.
2. In [Streamlit Community Cloud](https://share.streamlit.io), select **Create app → Yup, I have an app**.
3. Select that repository, branch `main`, and entrypoint `app.py`.
4. In **Advanced settings**, explicitly select **Python 3.14**.
5. Deploy; then verify the default February view, an alternate range, a no-record date and the source-period footer on the deployed site.

No secrets, API keys or external data downloads are needed at runtime. The committed small CSV keeps the demonstration reproducible. Notebook dependencies are in the development group, not the deployment requirements.

The code retains the repository owner's MIT license. Dataset attribution and Kaggle's reported CC0 data license are documented separately above.

### Individual submission

Although the team can share a dataset and design discussion, **each person must submit their own app, public repository and README**. Team15 is the group name; this repository is one student's submission and does not establish the identity or participation of other team members. Do not invent names or contributions. Review and understand the analysis before submitting, and disclose assistance if your course's policy requires it.

Submit the verified deployed app URL and this repository's URL on Canvas. `DEPLOYMENT.md` records the actual publication status and any remaining account steps.

## Sources

- [Assignment requirements](https://bana409.harrywang.me/docs/lectures/data-app/in-class-group-exercise), also supplied in the task conversation.
- [Coffee Sales dataset](https://www.kaggle.com/datasets/ihelon/coffee-sales).
- [Dataset author's introduction](https://www.kaggle.com/getting-started/521180).
- [Streamlit deployment instructions](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).
- [Streamlit AppTest documentation](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest).
