# Validation evidence — Team15

Validation performed locally on **12 October 2026**, using **CPython 3.14.7**, **Streamlit 1.65.0**, **Pandas 3.0.6**, and **Altair 6.3.0**.

- Source preparation retains 3,636 primary and 262 secondary rows; the published CSV is about 254 KB. Anonymous card identifiers are absent.
- Primary reconciliation: 115,431.58 source units; 3,636 rows; 31.75 average. All 89 primary cash transactions remain.
- Secondary reconciliation: 6,890.00 source units; 262 rows. Two identical extra rows remain explicitly qualified.
- The EDA notebook's seven code cells executed successfully; it includes three Matplotlib figures and source/quality summaries. The saved figures were visually inspected.
- Six automated checks passed: source totals and field exclusion; unknown-date handling; the illustrative decline rule; default/full-period app values; empty/incomplete date selections; and source switching with secondary duplicate notices.
- The app renders three metrics and two charts for a nonempty period. Switching source resets its coverage limits and applies its own date filter. No all-sources aggregate is offered.
- A local server started successfully and its health endpoint returned `ok`. The primary default page was inspected in the browser: February 2025 shows 13,215.48 sales, 423 transactions and a 31.24 average.

These checks establish local behavior. They do not establish a successful public Cloud deployment, validate the operational 20% threshold or confirm inventory and machine conditions.
