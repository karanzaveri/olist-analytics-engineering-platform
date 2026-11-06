# Business case interviews

Treat incident details as hypothetical. Use the linked artifacts to ground your definitions, then state what evidence you would seek. Give yourself 15–20 minutes per case.

| Case | Interview brief | Evidence to start from |
|---|---|---|
| Declining conversion | The weekly headline falls after mobile traffic rises. The product lead wants to redesign checkout. Give a triage order, a decision and a measurable trigger to revisit it. | [Historical funnel and attribution](../../../analytics/models/ga4/README.md) |
| Revenue anomaly | A purchase week shows a sharp revenue drop. Finance wants to revise next month's budget before checking the feed. Reconcile orders, payment values, eligibility and the data cutoff. | [Forecast boundary case](../../forecasting/README.md) · [Order fact](../../../analytics/models/marts/fct_orders.sql) |
| Customer retention | CRM claims a campaign failed because the newest cohort's repeat rate is lower. Specify eligible cohorts and distinguish exact-month from cumulative return. | [Cohort report](../../powerbi/customer-retention-page.md) |
| Delivery delays | The national average is stable, but two states report more complaints. Choose operational metrics and explain how undelivered orders affect the analysis. | [Delivery visuals](../../../dashboard/Data%20Analytics.Report/definition/pages/46270c605c5d9d24f127) |
| Pricing and profitability | A seller requests a 5% discount. Baseline is 1,000 units at BRL 100 and variable cost BRL 70 per unit. At an expected 15% volume increase, decide whether to test it. State what marketplace payment data can verify. | [Revenue and modeling definitions](../../../README.md#key-metrics-and-modeling-decisions) |
| Experiment rollout | A VP wants a full launch because the synthetic checkout test has a positive effect. Present the evidence required for a real decision, including economics and guardrails. | [Experiment decision and assumptions](../../../experimentation/CASE_STUDY.md) |
| Stakeholder disagreement | Finance calls payment totals revenue while merchandising uses item value. Both want the same executive card. Lead a definition agreement, reconcile the sources and propose ownership. | [Order reconciliation fields](../../../analytics/models/marts/fct_orders.sql) |

Score each dimension from **0** (missing or incorrect), **1** (partially specified), to **2** (correct and defensible). Aim for **8/10**, with no zero in metric definition or evidence.

| Dimension | Two-point standard |
|---|---|
| Decision framing | States the decision, owner, and time horizon |
| Metric definition | Names grain, numerator and denominator or monetary basis, population, and window |
| Evidence and diagnosis | Proposes a concrete validation sequence and tests a plausible alternative |
| Uncertainty | Identifies limits on causality, missingness or generalization that matter to the decision |
| Recommendation | Gives a specific action and a condition or measurable gate that changes it |

[Separate reference answers and case-specific scoring anchors](instructor/REFERENCE_SOLUTIONS.md)
