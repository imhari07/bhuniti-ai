# BhuNiti AI
## Team Nexora · Land Acquisition Intelligence and Decision Support

A local, upload-only application. The workspace starts empty. CSV contents, calculated values, what-if changes, officer notes and fitted estimators are never intentionally written to application storage. There is no database, saved upload directory, browser storage, analytics, external API call or request-body logging. Export is an explicit user action.

## Start on macOS

Prerequisites: Python 3.11 or newer and Node.js 22.12 or newer, with npm. Open this folder in VS Code.

```bash
cd "/Users/visrut/Documents/Codex/2026-09-10/referenced-chatgpt-conversation-this-is-an/outputs/bhuniti-upload"
./dev.sh
```

Open http://localhost:8000. First setup installs dependencies and needs internet. Later runs work offline. The launcher builds the frontend and serves it with FastAPI from one localhost port. Stop with Control-C. Do not run another application on port 8000 at the same time.

### Separate frontend and backend development

Terminal 1, from the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
PYTHONDONTWRITEBYTECODE=1 uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Terminal 2:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The development frontend calls the backend on port 8000, with cross-origin access restricted to the two local development origins. `npm start` also starts the frontend. No third-party fonts, map tiles or remote scripts are loaded. API documentation is at http://localhost:8000/docs. The portal includes an offline Leaflet coordinate map using uploaded parcel coordinates and source-referenced GeoJSON. It requests no external tiles.

## Workflow

1. Upload UTF-8 CSV, maximum 5 MB, 10,000 records, 100 columns, 20,000 characters per cell.
2. Inspect the first five records. Headers must be nonempty and unique; rows must have equal widths.
3. Map supported columns explicitly. No semantic mapping is guessed. Preserve case-sensitive 3a and 3A meaning.
4. Confirm land unit, amount unit, date format and project type. Unmapped fields stay unavailable. For unmapped dates or amounts, format choices have no effect.
5. Confirm compatible scopes and distinct/nonoverlapping projects only if justified. Otherwise portfolio totals remain unavailable.
6. Analyze quality, land progress, source evidence and recorded timeline gaps.
7. Select a record to inspect original values, formulas, operands, flags and actions.
8. Optionally change acquired land in a temporary arithmetic comparison. Original records and descriptive downloads retain baseline values.
9. Optionally enter officer review notes. They remain in React memory and are exported only if the notes checkbox is selected.
10. Download results and clear the session. Clear resets the file, mapping, results, notes, model report and file input and aborts pending browser requests. An already executing server calculation may finish before request-local memory is reclaimed; no persistent copy is created. A page reload resets project-analysis state. Portal sessions can be resumed using access codes until they expire or are closed. This is not a forensic memory-erasure claim.

## Structure

```text
frontend/
  src/App.jsx          upload, mapping, dashboard, charts and review workflow
  src/Community.jsx    citizen and official role-scoped workflows
  src/ProjectMap.jsx   offline uploaded geometry and parcel points
  src/styles.css       Tailwind entry and application styling
  vite.config.js       local development routing
backend/
  app/schemas.py       strict request contracts
  app/analysis.py      CSV validation, quality checks and direct calculations
  app/modeling.py      eligibility gate and request-local temporal evaluation
  app/community.py     expiring sessions, reports, status updates and timing decisions
  app/main.py          API and explicit CSV export
  tests/               implementation and model-contract checks
```

React + Tailwind + Recharts → FastAPI → pandas string-only data handling → pure calculations or guarded scikit-learn evaluation → browser results → explicit download. Project-analysis models and parsed datasets are request-local. Portal records are held in a separate two-hour shared memory session.

## Supported fields and units

Project identifier, project name, required land, acquired land, sanction amount/date, recorded 3a/3A/3D dates, observation date, source date/reference, planned completion, actual completion.

Land: hectares, acres or square metres, one confirmed unit for both fields and every record. One acre = 0.40468564224 hectare; one square metre = 0.0001 hectare. Amounts: INR, lakh INR or crore INR. Dates: ISO YYYY-MM-DD, DD/MM/YYYY or MM/DD/YYYY; no format detection. Notification date lists use semicolons. Other date fields must contain one date. Mixed-unit/date-format files must first be separated or normalized by the user.

## Calculation rules

- Progress (%) = acquired / required × 100.
- Remaining land = required − acquired.
- Remaining (%) = (required − acquired) / required × 100.
- Sanction INR per required hectare = amount × currency multiplier / (required × hectare conversion). This is not compensation per hectare.
- Adjacent recorded stage gap = earliest date in the later-stage list − latest date in the earlier-stage list. This is not parcel-matched stage duration.
- Portfolio progress = total acquired / total required × 100. Totals require valid land pairs in every row, confirmed compatible scopes and distinct projects, with no duplicate identifiers or identical rows detected.

Nonnegative finite numbers only. Required area must be positive for ratios. Acquired area greater than required suppresses all land-progress indicators. Missing values are not filled. Negative recorded date gaps remain visible and are flagged for context review. Missing dates do not prove incomplete stages. Highway stages are not applied when the file is declared other/mixed. Project IDs are preferred for display; a row ordinal is only an interface reference.

## Predictive eligibility and validation

Descriptive analysis always works to the extent supported by mapped fields. No delay probability or duration estimate appears by default.

Optional historical evaluation requires explicit user attestations and a written verification/source explanation. These attestations are not independent source verification. Each row must have a distinct project ID, valid land areas at the snapshot, source reference/date, observation date, original planned completion known at that snapshot, and actual completion outcome. The source date must be on/before the snapshot; both completion dates must follow it. Merely naming a column “delay” does not qualify it.

The implementation requires at least 100 records and 10 distinct snapshot dates. These are minimum engineering guards, not evidence of adequate sample size. It partitions the earliest 40%, next 20%, next 20%, and latest 20% of distinct snapshot dates. Equal-date rows stay together. Each partition needs at least 15 records and five examples of each outcome. All outcomes in each earlier partition must occur before the next partition begins. No row is silently dropped to make a split pass.

Target: actual completion later than the plan known at the snapshot. Four features are used: required hectares, acquisition progress, days from the snapshot to the original planned completion, and source age at the snapshot. Actual completion never enters the inputs. These historical land values must be verified as available at the snapshot; the software cannot establish that from the values alone.

Benchmarks: standardized, class-balanced logistic regression, a class-balanced random forest, gradient boosting, and XGBoost with balanced sample weights. Fixed seed 2026. Preprocessing fits only on training rows. Models are selected by Brier score (PR-AUC as tie-breaker) on the second chronological partition. The selected model receives logistic probability recalibration on the separate third partition. The latest fourth partition is untouched by fitting, selection or calibration. A training-prevalence baseline is scored on the same test records. Reported metrics include F1, precision, recall, ROC-AUC, PR-AUC, Brier, confusion matrix, class counts and calibration bins.

Historical test probabilities are displayed only when the selected model beats the prevalence baseline in test Brier score and has ROC-AUC above 0.5. Otherwise the evaluation report is shown without probabilities. This gate is not a deployment-readiness guarantee. No future-project prediction endpoint, saved model, duration model, cross-validation claim or individual predictive confidence interval is provided. Additional algorithms are not necessary to evaluate this four-feature contract. Global explanations use repeated held-out permutation importance measured as the increase in Brier error. Local explanations replace one input with its training median and show the probability difference. These comparisons need not sum to the prediction and may be infeasible combinations; they are not causal effects. The 95% bootstrap interval uses 300 resamples of test Brier error: it reflects aggregate sampling variability conditional on a fitted model, not uncertainty for an individual project.

The result is a historical evaluation, not an automatic production predictor. It is discarded with the request/session. Repeated evaluation of the same holdout can bias human decisions; do not treat a repeatedly inspected test set as unseen.

## Review and unsupported modules

Review actions are tied to invalid entries, missing evidence, inconsistent dates and remaining land. The application cannot approve acquisition, release funds or bypass procedures. Citizen impact and acquisition-timing comparison are available through the separate parcel-register contract described below. Emergency prioritization and computed spatial overlap are not implemented.

## Export and privacy boundaries

`/api/export` returns a CSV in memory with original columns plus indicators, flags, actions, recorded gaps and optional notes. Output column names are made unique. Formula-like spreadsheet cells are prefixed with an apostrophe; this is a documented safety transformation on download, not a source-record correction. Missing numeric outputs export as blank. Evaluation probabilities are not included in the descriptive CSV.

API responses use `Cache-Control: no-store`. No localStorage, sessionStorage, IndexedDB, service worker, database or file upload persistence is used. Access logging is disabled by the documented launch commands. Normal dependency installation/build files are code assets, not user records. The operating system and browser may manage memory independently; do not represent this design as cryptographic erasure. Downloaded exports are user-controlled files.

## API

- GET `/api/health`, `/api/fields`
- POST `/api/inspect`: CSV text
- POST `/api/analyze`: CSV text + confirmed settings
- POST `/api/what-if`: same + row index and assumed acquired area
- POST `/api/evaluate`: same + explicit verification attestations
- POST `/api/export`: same + optional notes and export choice

Every project-analysis request supplies its own input. The separate community API uses expiring in-memory sessions for citizen/official collaboration. Invalid requests return 422 without echoing the uploaded body.

## Tests

```bash
cd backend
../.venv/bin/python -m pytest -q -p no:cacheprovider
```

Tests construct small in-memory contract fixtures. They are never application records, are never preloaded into the UI, and are not evidence of real-world predictive performance.


## Version 2 upgrade

The overview includes source-field coverage and a review queue ordered explicitly by flag count, not delay likelihood. Historical evaluation uses four disjoint cohorts, four candidate models, calibrated probabilities, error uncertainty, permutation importance and local reference sensitivity. The model report can be downloaded as JSON only on explicit request. No data or estimator is saved automatically.

The six-record source CSV remains descriptive-only. The additional modeling capabilities have passed implementation tests, not real-world validation on that file.


XGBoost is installed and actively fitted in every eligible historical evaluation. CPU histogram trees, fixed seed 2026 and balanced training weights are used. It competes on the same selection partition; the winning model alone is calibrated on the separate calibration partition. XGBoost is not guaranteed to win, and the six-record upload remains descriptive-only.


## Version 3: citizen and official portals

Choose **Citizen & official portals** in the top navigation. The existing project-analysis workspace remains available. The original six-record project summary does not contain citizen/parcel associations or project geometry; those fields must come from an authorized supplemental register. The app provides a blank column template and starts without citizen records.

1. Official uploads an authorized parcel-register CSV; optionally includes source-referenced GeoJSON.
2. Server creates a two-hour session and an official access code. Under Access & explanation, reveal individual citizen codes only when needed. No invitations are sent automatically.
3. Open another browser tab, select Citizen entry, and enter the session ID and that citizen's private code. The server returns only the linked records and own reports.
4. Citizen submits a parcel-linked problem. Official selects Citizen reports, refreshes, responds and updates its review status. Citizen refreshes to read the response.
5. Official can record parcel status/compensation changes with source, observation date, officer and reason. Before/after values appear in the session audit export. No funds are transferred and no legal approval is executed.
6. Impact by area groups by project AND area, counts unique citizens with open reports, and divides by registered citizens in that group. Total reports and categories are shown separately. Counts measure reported concerns, not independently established harm.
7. Project map displays supplied geometry and coordinate points. Planned lines show alignment; only supplied polygons show stated coverage. No background map is downloaded, and no parcel-overlap calculation is claimed.
8. Acquire Now vs Wait requires two explicitly entered option estimates, declared scales, editable weights, a source/rationale, and officer identity. It displays each normalized component and its total. Unknown statuses, missing evidence, unresolved approvals, outstanding/unknown compensation or unconfirmed readiness block acquire-now review. These are conservative application checks, not legal rules.
9. Record an officer review decision and reason. If records or reports changed since evaluation, the server requires reevaluation. Export a role-filtered JSON if needed. Close shared session removes its data and invalidates all codes.

See [PORTAL_DATA_DICTIONARY.md](PORTAL_DATA_DICTIONARY.md) and [JUDGE_PORTALS.md](JUDGE_PORTALS.md) for the input contract, formulas and presentation script.

### Portal memory and access boundaries

No database, browser storage, uploaded file or citizen record is written by the application. Shared records DO remain in process memory for up to two hours, unlike request-local project analysis. A cleanup thread checks expired sessions every 30 seconds; expired sessions are inaccessible immediately on access. Leaving a view clears its browser state but does not close the shared session. Closing it or stopping the server discards the session. Explicit exports are files under the user's control.

Use one server process/worker. Sessions are not shared across workers or machines and do not survive restart. The local launcher binds only to 127.0.0.1: citizens can use a second tab on that computer, not their own remote devices. Network deployment, verified identity, MFA, persistent case management, tamper-evident audit storage and independent authorization administration require additional engineering. Anyone with local application access can create a new official session; the upload attestation is not independent identity verification. Never present this as a government identity system.

Citizen account association is one account per project/parcel. Co-ownership must be resolved by the authorized register owner before import; the app does not guess owners or divide compensation. A stolen access code grants the corresponding scope until session expiry/closure. Source references on project geometry must be suitable for all linked citizens to see; do not place private individual information there.

### Portal API

All session routes below require `X-Access-Code`; role checks run on the server.

- POST `/api/community/sessions`: verified register and optional geometry; creates session credentials.
- GET `/api/community/{session_id}`: role-filtered records/reports/map.
- GET `/{session_id}/invitations` under the community prefix: official-only citizen codes.
- POST `/{session_id}/reports`: citizen-only report for an owned parcel.
- POST `/{session_id}/reports/{report_id}/response`: official response and review status.
- POST `/{session_id}/parcel-update`: official sourced status update.
- POST `/{session_id}/evaluate-decision`: official option comparison with saved evaluation snapshot.
- POST `/{session_id}/decisions`: official decision tied to an unchanged evaluation.
- GET `/{session_id}/export`: authorized view only, no access codes.
- DELETE `/{session_id}`: official-only close.

The portal is descriptive and decision-support software. XGBoost remains in the eligible historical evaluation path; it does not predict compensation, citizen harm, report severity or the effects of acquiring now.


## Adjustable What-if risk assessment

What-if includes four manually supplied assumptions: compensation paid as a percentage of the total obligation, documentation completion percentage, percentage of parcels with unresolved disputes, and remaining approval wait in days. These are not automatically read from the uploaded project CSV. Blank inputs have no score. The optional midpoint button explicitly starts a 50/50/50/45-day comparison, with a 90-day reference.

Score = one quarter each of unpaid-compensation percentage, incomplete-documentation percentage, disputed-parcel percentage, and min(100, approval days / reference days × 100). Low is below 33; Medium is 33 to below 67; High is 67 or above, using the unrounded score. The 90-day reference is editable and is not a statutory deadline. Equal weights and thresholds are design assumptions, not trained coefficients or empirical risk cutoffs. Scores are assessment points, not probabilities.

Pin current comparison records the assumed inputs in component memory and shows point changes as sliders move. Changing the reference scale clears that comparison. Leaving What-if or switching projects resets these assumptions. No uploaded values, saved exports or historical model results are changed. The original acquired-land arithmetic comparison remains below. No causal delay reduction or validated delay prediction is claimed.
