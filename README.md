# Receipt Project

A personal receipt-processing pipeline that turns receipt images and PDFs into structured, queryable data.

Version 1 focuses on reliable receipt ingestion:

- capture receipts from a phone
- store them in OneDrive
- process them automatically with GitHub Actions
- extract structured receipt data with Google Gemini
- validate receipt totals
- deduplicate exact files and logical transactions
- persist structured data to Neon Postgres
- retain extraction JSON for audit/debugging
- route successful receipts to `processed`
- route questionable receipts to `review`

## Architecture

```text
iPhone / computer
        |
        v
OneDrive /Receipts
        |
        v
GitHub Actions
        |
        v
Receipt ingestion
   |            |
   |            +--> SHA-256 exact-file deduplication
   |
   v
Google Gemini
        |
        v
Structured receipt model
        |
        +--> /Receipts/extracted/*.json
        |
        v
Validation
   |           |
   | valid     | needs review
   v           v
Neon       OneDrive /review
Postgres
   |
   v
OneDrive /processed