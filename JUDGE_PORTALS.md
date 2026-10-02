# BhuNiti AI · Team Nexora — judge explanation

## 75–90 second presentation

“BhuNiti AI connects project evidence, citizen concerns and officer decisions. We begin with an uploaded CSV. The system checks completeness and consistency, then shows land progress and recorded timeline gaps with their formulas.

Our citizen portal uses an authorized parcel register. Each citizen receives access only to their linked land records and their own reports. They can see recorded approvals and compensation, submit a concern, and read the official response. The official can review all reports and update a status with its source, date and reason.

For area-level intelligence, we show both report counts and unique citizens reporting problems, together with the registered population denominator. We do not equate complaint volume with verified harm.

The map displays uploaded project alignment or coverage and parcel coordinates. Missing geometry stays unavailable.

Acquire Now vs Wait compares supplied estimates of schedule, cost and citizen disruption. Judges can inspect the weights, calculation and readiness checks. The officer retains the decision and records a reason.

XGBoost participates in historical evaluation only when verified outcomes and sufficient time-separated records exist. Our current six-record project file supports descriptive analysis, not a validated delay forecast. That distinction keeps every claim traceable.”

## Live walkthrough order

1. **Project analysis:** upload the existing source CSV, inspect it, confirm mapping/units, then show one calculated progress value and its original operands. Do not map collection date as observation date without source support.
2. **Citizen & official portals:** show the blank register template and explain that project totals cannot identify individual owners or compensation. Only open a populated session if an authorized parcel register is available.
3. **Citizen entry:** with that register, use a separate browser tab and a citizen code. Show own land, submit a genuine authorized test report in the local review session, then return to official view and refresh. Without register evidence, show the entry workflow and state what is missing.
4. **Official view:** show reports, area denominators, sourced status updates and audit. Reporting counts are observations about reports, not evidence of delay causation.
5. **Project map:** show supplied geometry if available. Explain planned line versus coverage polygon. If unavailable, show the explicit missing-evidence state.
6. **Acquire Now vs Wait:** enter officer-documented estimates or clearly labeled user assumptions, evaluate, inspect components and gates, then change one weight to show sensitivity. A numerical preference does not authorize acquisition.
7. **Close:** show the explanation panel and, if needed, explicitly export the review before closing the session. Do not display citizen access codes publicly.

## 15 likely judge questions

1. **What is actually AI here?** The eligible historical evaluation benchmarks logistic regression, random forest, gradient boosting and XGBoost. Data-quality checks, progress arithmetic, report aggregation and timing utility are transparent calculations, not learned models.
2. **Are you using XGBoost now?** It is implemented and trained during an eligible historical evaluation. The current six-row file does not meet the eligibility criteria, so we do not claim a trained, validated delay model for that file.
3. **What is the prediction target?** Actual completion later than the original planned completion known at the historical snapshot. Without verified dates and snapshot inputs, prediction remains unavailable.
4. **What accuracy have you achieved?** We have no defensible real-world predictive accuracy estimate on the six-record dataset. Automated tests check implementation behavior, not predictive generalization. Eligible evaluations report F1, recall, precision, ROC-AUC, PR-AUC and Brier on a separate test cohort.
5. **How do you avoid leakage?** Historical input values must predate outcomes. Chronological partitions separate fitting, selection, calibration and testing; earlier cohort outcomes must precede the next cohort. Actual completion does not enter input features. Source timing still requires human verification.
6. **Where do citizen records come from?** An authorized supplemental parcel register linking project, parcel and citizen account. We do not derive owners, compensation or citizen counts from project-level land totals.
7. **Can a citizen see another citizen’s data?** The API checks a private access code and filters records/reports on the server. The current local implementation uses possession-based codes, not independently verified identity. A leaked code grants its scope until closure/expiry.
8. **Do citizen reports prove harm?** No. They are statements to investigate. We count unique citizens with open reports and show the registered denominator. Reporting access and incomplete registration can bias comparisons.
9. **What does pending compensation mean?** Recorded total obligation minus recorded paid amount for the same parcel and scope, only when both fields are known. A known subtotal is explicitly distinguished from a complete total. Updating the record does not transfer money.
10. **How is the most affected area chosen?** We rank reported concerns by unique citizens with open reports, then open report count. We do not claim to identify the area with the greatest verified harm or unobserved population impact.
11. **How do you know the project will cover a place?** We display source-referenced uploaded geometry. A route line is alignment; only supplied polygons show stated coverage. We do not calculate legal parcel overlap or independently verify map accuracy.
12. **How does Acquire Now vs Wait work?** It compares declared estimates using normalized weights for schedule, incremental cost and registered-citizen disruption. Each component is visible. Weights and scales are preferences, not learned facts; sensitivity should be reviewed.
13. **Does a high acquire-now score authorize acquisition?** No. Conservative readiness gates can block the option. The officer must review applicable procedures and record a decision. The software neither grants legal authority nor predicts a causal benefit.
14. **Where are data and audit records stored?** Project analysis is request-local. Shared portal data remains in server memory for up to two hours and disappears on closure/restart. Explicit JSON downloads preserve a review under user control. This is not durable or tamper-evident case management.
15. **What remains before real deployment?** Authorized representative datasets and outcome validation; verified identity and access administration; durable audited storage and retention rules; secure network deployment; source integration; usability testing with actual citizens and officials; and independent review of procedural assumptions. Live learning is not implemented.

## Evidence and claim boundaries

| Item | Basis | Defensible statement |
|---|---|---|
| Project CSV | Uploaded source records | Displays supplied values; source quality still needs verification |
| Land progress and timeline gaps | Direct calculation | Traceable arithmetic, not proof of delay |
| Parcel status and compensation | Authorized register / sourced officer update | Recorded status, not a live government payment feed |
| Citizen problems | Citizen-entered statements | Concerns awaiting or receiving official review |
| Area reporting share | Derived from register and open reports | Registered citizens reporting concerns, not total harm |
| Project map | Uploaded coordinates / GeoJSON | Supplied alignment or stated coverage, no invented route |
| Timing option inputs | Documented estimates or labeled user assumptions | Explicit comparison inputs, not government dataset values unless sourced |
| Timing score | Visible weighted calculation | Preference under stated estimates, weights and readiness checks |
| XGBoost evaluation | Verified eligible historical outcomes | Historical model evaluation; unavailable on the current six-row file |
| Test fixtures | Isolated implementation tests | Software verification only; never real project evidence |
| Officer audit | In-memory timestamped review and explicit export | Review trace, not identity-verified or tamper-evident records |


## Explaining the adjustable What-if screen

“These sliders explore assumptions about compensation, documentation, disputes and approval wait. The visible rule assigns equal weight to each factor and classifies the resulting assessment as Low, Medium or High. I can pin one set of assumptions and show how the assessment changes. These are explicitly entered assumptions, not additional government records, and the result is not an XGBoost forecast or probability of actual delay.”
