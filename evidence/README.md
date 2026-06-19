# Evidence folder

| File | Purpose |
|---|---|
| `sample_upload.csv` | Demo CSV for the bulk-upload feature. Contains 5 valid rows and 1 deliberately bad row (`wellbeing_score=11`, max is 10) to demonstrate Scenario 1 failure injection. Upload it at `/cases/entry/upload/` while logged in as `operator1`. The bad row triggers a `ValidationError`, the error table is shown, and the entire batch is rolled back — zero entries are persisted. |

> To run the upload demo: seed the database first (`python manage.py seed_demo_data`) so that the `external_id` values in the CSV match real `Student` rows. If you are using a fresh database the rows will fail with "No student with external_id …" — which is itself a valid failure-injection test case.
