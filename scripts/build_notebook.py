"""Create and execute the course EDA notebook using this project's Python."""
import os
from pathlib import Path
import sys

os.environ.setdefault("MPLCONFIGDIR", "/tmp/team15-matplotlib")
os.environ.setdefault("IPYTHONDIR", "/tmp/team15-ipython")
os.environ.setdefault("JUPYTER_RUNTIME_DIR", "/tmp/team15-jupyter")
os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")

import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
md = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell
cells = [
    md("""# Coffee Sales EDA — Team15

**Decision-maker:** the operator responsible for coffee vending-machine ingredients and machine checks.

**Question:** how should recent drink demand influence ingredient priorities, and when does a decline justify an operational check?

This notebook uses Pandas and Matplotlib to inspect the data before choosing a deliberately small dashboard. The dataset is an author-reported real vending-machine transaction export from [Coffee Sales](https://www.kaggle.com/datasets/ihelon/coffee-sales), not an independently audited ledger. Both supplied files are kept in one prepared CSV without card identifiers, with explicit source tags. The dashboard analyzes one source at a time and defaults to the primary source. Amounts remain in **unverified source units**.
"""),
    code("""import json
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display
from dashboard import load_data, default_period, filter_period, headline_metrics, daily_counts, weekly_check

plt.rcParams.update({'figure.figsize': (11, 4), 'axes.spines.top': False,
                     'axes.spines.right': False, 'axes.labelsize': 11})
all_data = load_data()
data = all_data.loc[all_data.source.eq('index_1')].copy()
secondary = all_data.loc[all_data.source.eq('index_2')].copy()
audit = json.loads(Path('data/source_audit.json').read_text())
display(pd.DataFrame({'rows': [len(data)], 'columns': [len(data.columns)],
                      'start': [data.date.min()], 'end': [data.date.max()]}))
display(pd.DataFrame({'dtype': data.dtypes.astype(str), 'missing': data.isna().sum(),
                      'unique': data.nunique()}))
display(data.head())
"""),
    md("""## 1. Compare the supplied transaction streams

The table below is a saved audit of the two supplied originals, produced by `scripts/prepare_data.py`. Re-run preparation with the originals to reproduce its hashes and counts. Both sources' transaction fields are included in the small published CSV with provenance. Date overlap plus different product lists does not establish one common machine or business scope. We do not aggregate them into one trend or infer an unverified scope change as growth.
"""),
    code("""source_comparison = pd.DataFrame(audit['source_audits'])
display(source_comparison[['filename', 'bytes', 'rows', 'date_min', 'date_max',
                           'drink_categories', 'duplicates_all_fields', 'sales_source_units']])
print('Normalized matches between the two supplied files:', audit['normalized_cross_file_matches'])
print('Published CSV size:', audit['published_csv_bytes'], 'bytes')
display(pd.DataFrame(audit['source_audits'][0]['missing'].items(), columns=['original field', 'missing values']))
display(secondary.head())
print('Secondary recorded rows:', len(secondary), 'sales:', secondary.money.sum())
display(secondary[secondary.duplicated(keep=False)])
"""),
    md("""## 2. Completeness and reconciliation

The 89 absent card values in the original primary file all belong to cash payments. They are a payment-channel characteristic, not a reason to delete transactions. The published file omits the entire card identifier column. Required fields are complete, amounts are positive and dates agree with timestamps.

No-record dates are ambiguous: closure, genuine zero sales or incomplete capture could all produce them. We do not invent transactions or substitute zeros. The last date has no end-of-day completeness marker. Secondary-source duplicate rows are retained: timestamps are only precise to the second, and no transaction ID establishes whether these are distinct sales or duplicate exports. The dashboard flags them within the selected range.
"""),
    code("""assert len(data) == 3636
assert 'card' not in data
assert data.isna().sum().sum() == 0
assert (data.money > 0).all()
assert data.date.eq(data.datetime.dt.normalize()).all()
assert not data.duplicated().any()
assert data.cash_type.eq('cash').sum() == 89
metrics = headline_metrics(data)
assert round(metrics['sales'], 2) == 115431.58
display(pd.Series(metrics, name='full-period reconciliation'))
missing_dates = pd.date_range(data.date.min(), data.date.max()).difference(pd.DatetimeIndex(data.date.unique()))
display(pd.DataFrame({'dates without records': missing_dates}))
display(data.money.describe())
"""),
    md("""## 3. Distributions: transaction value and product demand

A value histogram is useful for checking unusual amounts but does not deserve a permanent chart on an ingredient-planning dashboard. The product count distribution directly informs the chosen business decision.
"""),
    code("""products = data.groupby('coffee_name').agg(transactions=('money', 'size'),
    sales=('money', 'sum'), average_transaction=('money', 'mean'), price_values=('money', 'nunique'))
products = products.sort_values('transactions', ascending=False)
display(products.round(2))
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
axes[0].hist(data.money, bins=15, color='#885336', edgecolor='white')
axes[0].set(title='Recorded transaction amounts', xlabel='Source units (currency unverified)', ylabel='Transactions')
products.transactions.sort_values().plot.barh(ax=axes[1], color='#C49063')
axes[1].set(title='Drink demand', xlabel='Transactions', ylabel='')
fig.tight_layout()
plt.show()
"""),
    md("""## 4. Time patterns and period selection

The default dashboard period is February 2025, the most recent fully elapsed month in the snapshot. March stops on the 23rd and should not be compared to a complete month as if coverage were equal. Even the last fully elapsed month must be checked for no-record dates.
"""),
    code("""start, end = default_period(data)
selected = filter_period(data, start, end)
display(pd.Series(headline_metrics(selected), name=f'default period: {start} to {end}'))
daily = daily_counts(data, data.date.min(), data.date.max())
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
axes[0].plot(daily.date, daily.transactions, color='#885336', linewidth=1)
axes[0].set(title='Daily transactions (gaps retained)', xlabel='Transaction date', ylabel='Transactions')
hourly = data.groupby(data.datetime.dt.hour).size().reindex(range(24), fill_value=0)
axes[1].bar(hourly.index, hourly.values, color='#C49063')
axes[1].set(title='Recorded transactions by hour', xlabel='Source-local hour (timezone unverified)', ylabel='Transactions')
fig.autofmt_xdate(rotation=30)
fig.tight_layout()
plt.show()
"""),
    md("""**Interpretation:** hourly patterns are interesting, but operating hours and staffing requirements are absent. We retain the daily trend for demand investigations and omit an extra hourly chart. This avoids turning every EDA finding into a dashboard element.

## 5. Relationships: product mix, pricing and sales

Revenue combines transaction volume and amount per transaction. Drink types have different prices, and each drink has multiple recorded amounts. Higher revenue therefore does not automatically mean more transactions or more ingredient demand. We use transaction ranking for planning priorities and keep sales plus average transaction amount as contextual headline numbers.
"""),
    code("""monthly = data.assign(month=data.date.dt.to_period('M').astype(str)).groupby('month').agg(
    transactions=('money', 'size'), sales=('money', 'sum'), average_transaction=('money', 'mean'))
display(monthly.round(2))
display(products[['transactions', 'sales', 'average_transaction', 'price_values']].round(2))
print('Largest transaction count:', products.transactions.idxmax())
print('Largest recorded sales:', products.sales.idxmax())
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
axes[0].scatter(products.transactions, products.sales, color='#885336')
for name, row in products.iterrows():
    axes[0].annotate(name, (row.transactions, row.sales), fontsize=8, xytext=(3, 3), textcoords='offset points')
axes[0].set(title='Volume and revenue differ by drink', xlabel='Transactions', ylabel='Sales (source units)')
axes[1].plot(monthly.index, monthly.average_transaction, marker='o', color='#C49063')
axes[1].tick_params(axis='x', rotation=60)
axes[1].set(title='Average transaction amount by month', xlabel='Month (last month is partial)', ylabel='Source units')
fig.tight_layout()
plt.show()
"""),
    md("""## 6. One proposed operational check

Compare recorded transactions in two consecutive seven-day windows. A decline of at least 20% prompts a data and machine review, not a causal diagnosis. This illustrative threshold is not calibrated to actual fault or stockout events: the data contains neither label. Suppress the comparison if either window has a no-record date or falls outside the selected range. Exclude the latest source date, whose full-day coverage is unverified.
"""),
    code("""check = weekly_check(data, start, end, data.date.max())
display(pd.Series(check, name='default-period seven-day check'))
assert check['current'] == 99 and check['previous'] == 119
assert check['status'] == 'within_threshold'
assert weekly_check(data, '2024-04-20', '2024-05-06', data.date.max())['status'] == 'unavailable'

history = []
for cutoff in pd.date_range(data.date.min() + pd.Timedelta(days=13), data.date.max() - pd.Timedelta(days=1)):
    result = weekly_check(data, data.date.min(), cutoff, data.date.max())
    history.append({'end': cutoff, 'status': result['status'], 'change': result.get('change')})
history = pd.DataFrame(history)
display(history.status.value_counts().rename('comparison dates'))
display(history.loc[history.status.eq('review')].head())
"""),
    md("""**Interpretation:** the default check is 99 versus 119 transactions, a 16.8% decline. It does not cross the proposed threshold, but that is not evidence that the machine is healthy. Counts of historical threshold crossings show how often the proposal would prompt review, not its precision or business value. These would require verified operating incidents.

## 7. Final design decision

**Three KPIs:** sales in source units, recorded transactions, and average transaction amount. All follow the date filter.

**Two charts:** daily recorded transactions and the top eight drinks by transaction count. Show calendar gaps, state any categories outside the top-eight chart, and do not imply exact inventory or profit calculations. Headline totals include all drink types.

**Two filters:** source export and inclusive transaction dates. No verified machine/location key exists, so the source selector is labelled as provenance, not as machine identity. Switching source changes the coverage limits and default dates.

**Omitted:** payment pie, anonymous customer leaderboard, hourly chart, raw transaction table, stockout and profit metrics. These either do not change this operator's chosen action or cannot be computed reliably.

**Order:** title/persona → period → KPIs → qualified check → two explanatory charts → data-period/refresh footer → collapsed limitations.

**Production cadence:** nightly transaction ingestion; daily exception review; weekly ingredient prioritization. The delivered demo is a frozen snapshot with no live refresh.

**Sources and reproducibility:** [Kaggle dataset](https://www.kaggle.com/datasets/ihelon/coffee-sales), [author introduction](https://www.kaggle.com/getting-started/521180), prepared CSV and saved source audit. README answers the assignment's Steps 1–4 in detail. No actual operator interviews, incident labels or savings estimates are claimed.
"""),
]
notebook = nbf.v4.new_notebook(cells=cells)
notebook.metadata = {
    "kernelspec": {"display_name": "Python 3.14", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": ".".join(map(str, sys.version_info[:3]))},
}
destination = ROOT / "eda.ipynb"
nbf.write(notebook, destination)
client = NotebookClient(notebook, timeout=90, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}})
client.execute()
nbf.write(notebook, destination)
print(f"Executed {sum(cell.cell_type == 'code' for cell in cells)} code cells; saved {destination.name} ({destination.stat().st_size:,} bytes).")
