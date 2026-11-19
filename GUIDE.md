# SOCHI Course Review — field guide

## Run a semester review

1. Open each of the four experimental course lists in Google Sheets: Ross MBA, Ross BBA, General Graduate and General Undergraduate. Choose File → Download → Microsoft Excel (.xlsx). Keep both Courses and Not Current tabs.
2. On the Registrar Schedule of Classes page, download the target term’s All classes CSV, including closed classes. Sign in through U-M if prompted. Do not upload the Open classes CSV: absence from that file would be misleading.
3. Upload the four Excel workbooks and the CSV, select the matching term/year, and click Compare courses. Optional historical CSVs add evidence; filenames should identify the actual term, for example FA2026.csv.
4. Filter the review queue. Inspect the source and evidence for each proposed update. Choose Accepted, Rejected or leave Pending. Add a note for ambiguous records.
5. Export the review CSV. It includes every original row locator, suggestion, evidence and your decision. Only manually copy Accepted changes into a COPY of the appropriate spreadsheet. Save review session downloads a JSON file that Resume session can reopen.

## What each action means

Update term offered: exact subject and catalog number found with a compatible title. Existing Fall/Winter terms are preserved. Verify A/B part-term, section and course link before accepting.

Reactivate course: a Not Current record has a matching target-term offering. After approval, move the row into Courses on your spreadsheet copy, remove Not Current from Term Offered and preserve all other tags and fields.

Review possible renumbering: the trained ridge model ranks a similar title with a different identifier. A score is NOT a probability, proof of identity or confirmation of renumbering. Confirm against the department catalog. Do not accept a different course because its name looks similar.

Review topic / title: an identifier may refer to a different special topic or section, or the Registrar’s short title may not be enough to establish identity. Check the full catalog before updating.

Review missing offering: absence next term is not discontinuation. Keep seasonal Fall/Winter courses available. Only choose Mark Not Current after confirming that the course has not been offered for MORE than one year; record the last offering and the historical sources in your note. The tool never automatically moves or deletes a record.

## Discover courses and review catalogs

Courses to investigate lists identifiers not in your uploaded lists whose titles match explicit social impact / environmental sustainability terms. This is a candidate search, not exhaustive discovery and not proof a course is newly introduced. Read the full description, establish the correct school and undergraduate/graduate audience, and apply Glenn’s inclusion criteria and approved taxonomy.

The Resource Cheat Sheet requires a clear societal or regional impact; environmental sustainability means ecological preservation/climate rather than generic biology/geology. Vague impact needs manual review. Review school catalogs even when no title-based candidates appear. Catalog coverage explains the central-schedule coverage and remaining manual work for each source.

Before publishing through WordPress, manually add the new semester’s valid labels to the Key tab, inspect part-term labels, move approved rows, update table ranges and test links. The app does not edit the website or source spreadsheets.

## Optional U-M toolkit

Core analysis makes no network calls and needs no API key. Glenn’s BUS-UMSI-for-Impact toolkit was successfully tested on November 19, 2026 using gpt-4.1-nano. The live app’s optional U-M review button requires UMGPT_API_KEY and a separate UMGPT_REVIEW_TOKEN set privately in Render environment settings. The reviewer enters the project review token to prevent public use of the funded key. It sends at most ten public course titles/identifiers to https://api.toolkit.umgpt.umich.edu/v1/messages. Never place the key in source code or the browser. Without the key, use the Open Glen’s toolkit link. U-M results are suggestions; they cannot establish offerings or approve changes.

## Model and limits

The ridge linear regression was trained locally on real experimental workbook courses paired with the Winter 2027 Registrar schedule. Positive weak labels come from identical subject/catalog identifiers; hard negative candidates use distinct identifiers within a subject. Features measure title similarity, overlap, relative length, subject and course level. Exact identifier equality is excluded from the model features to avoid learning the labeling rule directly. Training, validation and test use disjoint source course identifier groups.

The bundled model evaluation is available at /model. Weak labels may include reused special-topic numbers and cross-listed courses; the test is not human-adjudicated renumbering ground truth. The model supports a human review queue and never overrides schedule evidence. A local deterministic exact-identifier lookup handles confirmed availability.

Limits: .xlsx only (no legacy .xls), 10 MB per workbook, 15 MB per CSV, 30 MB encoded request total, 12,000 rows per course tab, 150,000 schedule rows, eight historical schedules. No live Google Drive sync, school-specific scraping, autonomous publication, exhaustive discovery, or automatic discontinuation decisions. Exported CSV values are escaped against spreadsheet formula injection.

## Privacy and operation

Uploads remain in request memory and are discarded after the response; no database, upload directory or API request-body logging. Review decisions stay in this browser session until you download them; refresh loses unsaved work. The public app is designed for public course data, not student records. Render’s free service may sleep when unused and take time to wake. No paid resources are required.

## Scope and sources

This implements the Fall course-checking scope confirmed in Meeting Minutes (October 24) and Nicole’s scope email (October 20). Events, colleagues, volunteering, clubs and careers are future expansion areas, not completed by this course tool.

Project Intake: https://docs.google.com/document/d/1352fg03VV-uYD-rYatkjPR0xVOnYOEQL6AbSz2hInsA/edit
Meeting Minutes: https://docs.google.com/document/d/1LwH5fy_Jh1y2BaK6_v7W531sADOEeNHHVVl293MJK8k/edit
Preliminary Research: https://docs.google.com/document/d/1jqiiGU7h_IAzDOIjBcBjNOr5BCOLov7vKBhzuKk335E/edit
Resource Cheat Sheet: https://docs.google.com/document/d/1JAAN9rUqQ9j6D8HW2Zc7u1ENW4vPBR1jKHzB3vqYZWU/edit
Registrar: https://ro.umich.edu/calendars/schedule-classes
Experimental workbooks: https://drive.google.com/drive/folders/1RHUNzI3mheNyOnIFjsrqCmPTcY6l_z1t

## Maintainer commands

Run locally: pip install -r requirements.txt; python app.py. Open http://127.0.0.1:8090.
Test: python -m unittest discover -s tests -v.
Train: install NumPy in your local environment, put four workbook exports and WN2027.csv in data/raw, and run python train.py. Raw data is excluded from Git. Review reports/model_evaluation.json before replacing models/ridge.json.
Production: gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120 app:application.

## Hairline catalog drawers

The catalog is an interactive isometric line figure: pointer selection opens one drawer, with neighboring changes staggered by distance. It uses Hairline’s unchanged engine and bench. Open /hairline-catalog.html?play=1 to run its tour. The drawer labels correspond to the four course lists; the figure is illustrative, not a data chart.
