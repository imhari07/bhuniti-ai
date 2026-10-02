# BhuNiti AI model and decision-support report

Reviewed: 2026-09-14. Application version 3.0.0; historical modeling module 2.1.0.

## Current source dataset

The separately supplied `bhuniti_real_upload.csv` has six rows and 21 columns, comprising a Bhoomi Rashi highway project record and parliamentary railway-project records. It is not automatically loaded or bundled into the application. Source references and limitations accompany the records. Collection date is not assumed to be observation date. Mixed scopes and project types prevent unsupported portfolio aggregation or universal highway-stage interpretation.

**No valid delay target is available in this file.** It lacks verified original planned and actual completion outcomes and verified historical feature snapshots. No delay labels were manufactured. No real-world classification metrics, calibration curve, feature importance, trained artifact or delay-duration estimate can honestly be reported for these six rows. Class balance and last-trained time are not applicable.

Available outputs are descriptive data-quality checks, recorded timeline gaps, land arithmetic and evidence-linked review actions. Optional portal records and geometry must be uploaded separately. Citizen concerns do not become delay outcomes.

## Implemented historical evaluation

When a different authorized upload satisfies the documented evidence and size gates, four classifiers are fitted: logistic regression, random forest, gradient boosting and XGBoost. Four inputs: required hectares, acquired percentage, days to original plan at snapshot, source age at snapshot. Actual completion is used only for the outcome. Seed 2026.

Chronological 40/20/20/20 partitions separate training, selection, calibration and testing. Selection uses Brier score, with PR-AUC as tie-breaker. Class balancing is applied. Logistic probability recalibration uses a separate cohort. Metrics include F1, recall, precision, ROC-AUC, PR-AUC, Brier, confusion matrix and calibration bins. This implementation uses disjoint temporal holdouts, not cross-validation.

Test probabilities are withheld unless the calibrated model beats a prevalence baseline in test Brier and exceeds 0.5 ROC-AUC. Global explanations use repeated held-out permutation importance. Local explanations compare an input with its training-median reference. Neither is causal. An aggregate test-Brier bootstrap interval is not an individual project confidence interval.

No future-project serving endpoint, saved trained estimator, duration model, SHAP claim or live retraining is included. Eligible evaluation reports can be explicitly downloaded; fitted models are request-local. Source timing verification still depends on the uploader. Minimum row counts do not prove sample adequacy or representative coverage.

## Citizen impact and timing decision layer

Impact uses recorded parcel statuses, known compensation amounts, report counts, unique reporting citizens and registered denominators. It does not predict injury, displacement, legal outcomes or report severity.

Acquire Now vs Wait is a multi-criteria comparison of supplied schedule, cost and citizen-disruption estimates. It uses explicit normalized weights and declared scales, with conservative readiness checks. Its output is estimated utility, not a probability or XGBoost result. The officer records a reason and a snapshot is retained until session expiry or explicit export. See PORTAL_DATA_DICTIONARY.md for exact formulas and gates.

## Verification and limitations

Seventeen automated tests passed on 2026-09-14, including historical leakage boundaries, citizen scope, missing compensation, report denominators, map-input validation, timing arithmetic, readiness gates, audit staleness and session closure/expiry. Tests use isolated contract fixtures and provide no real-world predictive performance evidence. Production frontend build passed. Python 3.14 reports dependency deprecation warnings without test failures.

Portal entry screens were checked in the running browser. No authorized citizen register or source geometry was available for a populated real-data visual walkthrough. These modules have API contract tests and a compiled interface; they still need acceptance testing with the authorized register owner and actual intended users.

The server is local-only and single-process. Two-hour memory sessions, possession-based access codes and unsigned exports are insufficient for production identity, durable case management or tamper-evident auditing. No government integration or legal authority is claimed.


## Adjustable What-if risk assessment

What-if includes four manually supplied assumptions: compensation paid as a percentage of the total obligation, documentation completion percentage, percentage of parcels with unresolved disputes, and remaining approval wait in days. These are not automatically read from the uploaded project CSV. Blank inputs have no score. The optional midpoint button explicitly starts a 50/50/50/45-day comparison, with a 90-day reference.

Score = one quarter each of unpaid-compensation percentage, incomplete-documentation percentage, disputed-parcel percentage, and min(100, approval days / reference days × 100). Low is below 33; Medium is 33 to below 67; High is 67 or above, using the unrounded score. The 90-day reference is editable and is not a statutory deadline. Equal weights and thresholds are design assumptions, not trained coefficients or empirical risk cutoffs. Scores are assessment points, not probabilities.

Pin current comparison records the assumed inputs in component memory and shows point changes as sliders move. Changing the reference scale clears that comparison. Leaving What-if or switching projects resets these assumptions. No uploaded values, saved exports or historical model results are changed. The original acquired-land arithmetic comparison remains below. No causal delay reduction or validated delay prediction is claimed.
