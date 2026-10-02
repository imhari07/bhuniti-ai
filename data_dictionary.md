# BhuNiti AI data dictionary

The application starts empty and maps uploaded project fields explicitly. The separately supplied six-record source file has the following columns. Do not infer missing values or convert collection time into source observation time.

| Source column | Interpretation |
|---|---|
| project_name | Source project title |
| project_id | Source identifier where available; blank does not establish a unique project |
| source_organization | Organization named in the collected source |
| source_reference | Source URL or document reference |
| source_locator | Table/page/section locator |
| source_date | Report date when explicitly available |
| collection_date | Date the information was collected; not necessarily the status date |
| state_context_raw | Unnormalized geographic wording from the source |
| land_required | Source required area; confirm hectares and scope before mapping |
| land_available_ha | Source available land, not assumed acquired land |
| land_to_be_acquired_ha | Source field, not automatically remaining balance |
| land_acquired | Recorded acquired land; confirm unit and matching scope |
| balance_land_to_be_acquired_ha | Source-reported balance where present |
| sanction_number | Source sanction reference |
| sanction_date | Recorded sanction date |
| sanction_amount | Project sanction amount in normalized INR, not compensation |
| notification_3a_number_raw | Source notification reference |
| date_3a | Recorded lower-case 3a date where supplied |
| notification_3A_numbers_raw | Source upper-case 3A references |
| date_3A | Recorded dates; multiple dates separated by semicolons |
| source_limitations | Record-specific caveats to preserve |

Derived land indicators and date-gap formulas are documented in README.md. Missing/invalid operands suppress unsupported calculations. Planned completion, actual completion, observation snapshot, citizen/parcel associations and route geometry are not supplied by these columns. Historical model eligibility therefore fails on the existing file.

For the additional citizen register, reporting fields, geometry contract and timing estimates, see [PORTAL_DATA_DICTIONARY.md](PORTAL_DATA_DICTIONARY.md). The UI downloads a header-only parcel template. Do not populate it with invented government or citizen values.
