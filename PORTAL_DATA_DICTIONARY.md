# Portal input contract

The project summary CSV and parcel register serve different purposes. Do not fill missing citizen fields from project-level totals. Use UTF-8 CSV with a header and one row per project/parcel. Maximum 3 MB and 3,000 records; fields at most 1,000 characters. The register is verified by the uploader, not independently authenticated by the software.

| Column | Required | Meaning / accepted values |
|---|---|---|
| project_id | Yes | Stable project identifier; use the existing project identifier where applicable |
| parcel_id | Yes | Parcel identifier unique within the project |
| citizen_id | Yes | Authorized account identifier from the verified association register; no identity-document number needed |
| area_name | Yes | Consistent named reporting area; grouped separately within each project |
| citizen_name | No | Display name; visible only within authorized scope |
| project_name | No | Supplied project name |
| acquisition_status | No | acquired, pending, partial, unknown; blank becomes unknown |
| approval_status | No | approved, pending, rejected, unknown; blank becomes unknown |
| compensation_due_inr | No | Total recorded compensation obligation in INR, not just unpaid amount |
| compensation_paid_inr | No | Recorded amount paid toward that same obligation and scope |
| land_area_ha | No | Parcel area in hectares |
| latitude, longitude | No | Both together, decimal degrees; ranges ±90, ±180 |
| status_date | No | Source observation date YYYY-MM-DD, not a future date |
| source_reference | No | Traceable reference for the supplied parcel status |

Monetary/area values must be finite, nonnegative and at most 1e15. Paid cannot exceed total due. Blank amounts remain unknown. Outstanding compensation = total due − recorded paid only when both exist. Known subtotals are explicitly labeled if any records are incomplete. A source's definition and scope must be checked before mapping.

## GeoJSON

Upload an optional FeatureCollection, at most 1 MB, 300 features and 30,000 positions. Supported geometries: Point, LineString, MultiLineString, Polygon, MultiPolygon. Positions are [longitude, latitude] in decimal degrees, two dimensions only. Polygon rings must close. Each feature needs properties.project_id matching the parcel register, properties.stage (planned / under_acquisition / acquired / unknown), and a nonblank properties.source_reference. properties.area_name is optional. No topology or source-authority verification is performed. A valid polygon is not automatically a verified legal boundary. Self-intersections and overlap are not evaluated.

The map is an offline coordinate display without external basemap tiles. Citizen views include project geometry only for linked projects, plus their own parcel points. Official views include all imported geometry and parcels. Route lines do not establish the width of a corridor or which parcels intersect it.

## Reports, impact and audit

Citizens choose a linked parcel, category and description. The server derives citizen ID and area from the authorized association, assigns time/identifier, and prevents duplicate open reports for the same account/project/parcel/category. Categories: compensation, approval, access, livelihood, records, other. Reports are citizen statements; officials can respond with received, under_review or resolved. Resolution is an officer-recorded status, not proof a payment occurred.

Reporting share = unique citizens with unresolved reports in project/area ÷ registered citizens in that project/area × 100. Multiple reports by one person count once in the numerator. The registered denominator may not cover all affected residents; reporting access can bias comparisons. No unobserved population, severity score or displacement count is inferred.

Status audit retains before/after values, source/date, officer, reason and timestamp in the expiring session. Decision audit retains supplied estimates, weights, scales, readiness gates, parcel snapshot and report summary. Officer names are supplied claims. Exports are not signed or tamper-evident.

## Acquire Now vs Wait

Input both options' days to the SAME defined milestone, incremental INR cost measured over the SAME horizon, and estimated disrupted citizens within the registered project population. State the wait duration in the rationale. Label the basis as documented estimates or user-entered assumptions and supply sources. The software cannot verify these estimates.

All objectives are minimized. Normalize nonnegative weights to sum to one. Each option's utility is:

`100 × [w_schedule × (1 − days / schedule_scale) + w_cost × (1 − cost / cost_scale) + w_citizen × (1 − disrupted / registered_citizens)]`

Declared positive schedule/cost scales must cover both options. Default editable weights are 0.4, 0.3, 0.3, representing a preference choice. Scores are not probabilities. Changing a scale changes the tradeoff and must be justified. The option with higher estimated utility is preferred only within the stated assumptions and subject to readiness gates. Equal scores require officer review. Results do not identify a causal effect, a best date, or a legal entitlement.

Checks prevent acquire-now review when there are unknown acquisition statuses; approvals not recorded as approved; missing compensation; outstanding compensation; absent source/date; no procedural confirmation; or all parcels already acquired. These conservative checks may be stricter than a jurisdiction's actual procedure. Freshness has no invented universal deadline: the officer must assess the status date and confirm readiness. Readiness is assessed across the whole registered project, not an optimized subset.
