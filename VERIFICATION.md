# Verification

- Eight automated tests passed: CSV structure; feature arithmetic and timeline gaps; missing/invalid values and duplicates; scope and format gates; what-if nonmutation; safe CSV export and optional notes; historical eligibility rejection; temporal evaluation and future-outcome leakage rejection.
- Production React/Tailwind/Recharts build passed. Chart code is bundled separately.
- Browser check using an existing user-owned real CSV: upload recognized six records and 21 columns; explicit mappings produced six valid land pairs; incompatible/unconfirmed portfolio totals were withheld.
- Browser what-if check: first record retained baseline progress approximately 0.845%; changing acquired land to 100 hectares produced 50% arithmetic progress while leaving baseline values visible.
- Browser clear-session check returned to the empty upload screen with no project table, file name, calculations or notes visible.
- Application-source scan found no browser-storage or persistent-record write operations.
- Application-authored source and documentation passed the requested terminology check.
- Historical-model tests use in-memory contract fixtures and verify mechanics only. No real-world predictive validation is claimed.
- Python 3.14 emitted dependency deprecation warnings; all tests passed.

## Version 2 verification

Nine tests passed, including confirmation that changing only final-test outcomes does not change model selection or calibration. Three candidate estimators, four disjoint cohorts, four features and local explanations are covered. Production build passed. Browser verification with the six real source records showed the new evidence briefing and review queue; this dataset remains in descriptive mode.

## Version 2.1

XGBoost 3.4.1 installed and successfully fitted during eligible evaluation tests. All nine tests pass, including presence and valid Brier results for XGBoost. Frontend build passed. Four algorithms share the same selection partition, with separate calibration and final test partitions.


## Version 3 verification (2026-09-14)

- All 17 automated tests passed; production frontend build passed.
- Eight portal tests cover server-side role restrictions, own-record exports, report ownership/deduplication/responses, project-area denominators, unknown compensation, weighted timing arithmetic, readiness gates, sourced status updates, stale evaluations, geometry validation and closure/expiry.
- Browser opened the running application and verified the new portal navigation, upload/attestation controls and citizen/official entry screens. No authorized populated citizen register or geometry was available for a real-data visual walkthrough.
- Shared portal records intentionally remain in process memory for two hours; no database or upload persistence was introduced. The earlier request-only description applies to project analysis.
- The 17 passing tests include isolated fixtures. Their model metrics must never be cited as project performance.


## Adjustable What-if verification

Three JavaScript test groups passed: missing/invalid inputs, extreme values and exact band boundaries, direction of change, approval-component saturation, contribution totals and input nonmutation. These validate the transparent assessment mechanics, not predictive accuracy. Run with `cd frontend && node --test tests/riskAssessment.test.mjs`.

Updated production frontend build passed; running local app returned HTTP 200.
