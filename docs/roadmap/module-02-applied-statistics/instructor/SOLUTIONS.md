# Instructor solutions · Applied Statistics & Business Cases

## 1. Delivery tail

| State | Orders | Mean days | Median | P90 | Maximum | Upper fence | Above fence |
|---|---:|---:|---:|---:|---:|---:|---:|
| SP | 2,712 | 6.64 | 6 | 11 | 68 | 14 | 155 |
| RJ | 696 | 9.50 | 8 | 16.5 | 41 | 18.5 | 53 |

The mean and median are useful for a typical order, while P90 informs a service-risk threshold. Compare within the same date window and inspect timestamp validity, routes, tracking gaps and exceptional delays. A plausible delay remains in service reporting. A tail flag identifies a record to inspect. Validate `SP + RJ = 3,408` and apply the fence with strictly greater than.

## 2. Delivery sampling audit

The deterministic sample contains **2 late of 100**, and the Wilson illustration gives approximately **0.55%–7.00%**. The full eligible SP slice is **100 of 2,712 (3.69%)**. The selection rule is reproducible but supplies no documented random sampling guarantee. For a probability sample, randomly draw without replacement within state from the eligible frame. Weight by each state's share of eligible orders when estimating the combined share from disproportionate strata. State each frame, period and missingness rule. Undelivered orders fall outside this completed-delivery estimand. The pooled completed frame has **117 late of 3,408**.

## 3. Conversion replanning

Use the repository's two-sided normal approximation with Cohen's h and round each arm up. At 1 pp and alpha .05, target **17,164 per arm**. At 2 pp and alpha .01, target **6,596 per arm**. The original plan uses **4,433 per arm**. The seed-42 p-value is approximately **.01551**, below .05 and above .01. Under the null and test assumptions, it is the probability of a test statistic at least as extreme as observed. Power is the probability of rejecting the null under a specified alternative and design. A future test should prespecify its meaningful effect, alpha, allocation and stopping rule. Under the traffic cap, compare a longer recruitment window, a larger meaningful target, or explicitly lower planned power. Validate that both new designs need more traffic than the original.

## 4. SRM incident

The export contains **4,433 A and 4,083 B**. The expected count is **4,258 per arm**, giving **chi-square 14.38469**, one degree of freedom and **p ≈ .000149**. Pause effect interpretation. Reconcile unique eligible IDs against the ledger, locate the first stage where B rows disappear by date/device/version, then repair and rerun against a complete, independently checked analysis population. Check outcomes and guardrails separately. The original synthetic equal split is fixed by construction. An apparent p-value in a damaged export cannot establish that outcome collection remained comparable.

## 5. Delivery regression

| Slice | Pearson r | Slope in actual days per promised day |
|---|---:|---:|
| Pooled | .41853 | .26377 |
| SP | .39819 | .30736 |
| RJ | .28594 | .18061 |

Check the signs and the sample counts from case 1. Different state slopes suggest the pooled association compresses heterogeneous patterns. Route difficulty, distance and carrier selection can influence both estimated and actual time. State stratification leaves confounding within states. An ethically reviewed randomized test of the displayed promise could estimate its effect on conversion or complaints while fulfillment remains comparable. For delivery-time effects of a logistics intervention, randomize the operational change where feasible and track actual lead time and harms.

## 6. Retention and conversion

June M1 is **25 / 5,878 ≈ 0.4253%**. July M1 is **31 / 5,949 ≈ 0.5211%**. Weighted M1 is **56 / 11,827 ≈ 0.4735%**. August has **6,144** first observed delivered buyers in this local computation, and September M1 is unobserved under the August cutoff. Validate using distinct customer identities and exact month age. A 0.0958 pp observed increase with small numerators deserves caution. These are first observed delivered purchases within the historical extract.

The historical GA4 numerator is **226 sequential purchasing sessions**. All-session conversion is **226 / 26,355 ≈ 0.86%**, while view-entry conversion is **226 / 6,192 ≈ 3.65%**. With desktop **114 / 15,354** and mobile **107 / 10,413** held fixed, the synthetic 70:30 mix yields **~0.828%** and the 30:70 mix **~0.942%**, about **0.114 pp** apart. This isolates mix arithmetic. The observed device association provides no estimate of a device intervention effect.

## 7. Revenue forecast loss

Using signed error `forecast − actual`, compute `max(error,0) + 3 × max(−error,0)` per week. On the 12 matching dates, mean scores are **Naive 68,315.20**, **MA4 103,635.89**, and **MA8 102,434.45** in BRL-scaled loss units. Naive wins this specific scenario. Validate that a 100 BRL underforecast costs 300 under the rule. The weight is hypothetical and needs operational justification. Replay with an as-of timestamp for inputs and target maturation, train only on values available at each origin, and track several later origins before authorizing a forecast-based commitment. Final delivered status can leak information backward into prior purchase weeks even when row dates are sorted.

## 8. Example executive memo

Prioritize a delivery investigation in RJ. July's completed sample has **P90 16.5 days across 696 RJ orders**. Operations should review carrier and route concentration and verify that undelivered orders do not materially change the picture before setting a revised service target.

Retention has **56 exact-M1 returns across 11,827 eligible June and July buyers**. CRM should compare mature cohorts at matched ages before expanding spend. The synthetic conversion export has an SRM flag at **p ≈ .000149**. Experimentation should reconcile exported users to assignments, then measure guardrails and confirm the economics before a rollout decision. Finance can use Naive as a retrospective planning reference, with **68,315.20 BRL-scaled mean loss over 12 targets** under the assumed rule. Require point-in-time validation before allocating budget from that forecast.

A valid alternative priority names the decision owner, keeps dates and denominators visible, distinguishes Olist observations from synthetic evidence, and states a measurable condition that would change the decision.
