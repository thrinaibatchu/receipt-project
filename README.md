# Receipt Project

A personal receipt ingestion and analytics system that turns receipt images, PDFs, and historical purchase data into structured, queryable information.

## Version 2

Version 2 combines automated receipt ingestion with a read-only analytics application.

The system currently supports:

- receipt capture through OneDrive
- scheduled processing with GitHub Actions
- structured receipt extraction with Google Gemini
- validation and duplicate detection
- Neon Postgres persistence
- historical Costco purchase import
- Streamlit analytics dashboard
- transaction, spend, item, and price analytics
- natural-language receipt questions
- deterministic effective-price calculations
- limited canonical product routing for known product aliases

## Architecture

```text
                    RECEIPT PROJECT V2

LIVE RECEIPTS
─────────────

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
        |
        +--> SHA-256 exact-file deduplication
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


HISTORICAL DATA
───────────────

Historical Costco purchase data
        |
        v
Deterministic import pipeline
        |
        v
Validation / overlap protection
        |
        v
Neon Postgres


ANALYTICS
─────────

Neon Postgres
        |
        v
Read-only analytics connection
        |
        +-----------------------------+
        |                             |
        v                             v
Deterministic analytics          Natural-language analytics
        |                             |
        |                             v
        |                        Gemini NL -> SQL
        |                             |
        +-------------+---------------+
                      |
                      v
               Streamlit dashboard
```

## Data Model

Primary tables:

```text
receipts
receipt_items
receipt_discounts
products
```

`receipts` represents transactions.

Transaction semantics:

```text
purchase       total > 0
return/refund  total < 0
zero-value     total = 0
net spend      SUM(total)
```

Historical receipts are identified separately from live receipts using `source_type` and `historical_key`.

## Analytics

The Streamlit dashboard includes:

- transaction count
- purchase count
- returns / refunds
- net spend
- spend over time
- spend by store
- top items by quantity
- top items by spend
- item search
- recent transactions
- transaction detail
- Ask Your Receipt Data

Analytics use the read-only `ANALYTICS_DATABASE_URL` connection.

## Natural-Language Questions

The application uses a hybrid query approach.

General analytics questions use constrained read-only natural-language-to-SQL generation.

Example:

```text
How many times did I buy milk in the last 90 days?
```

Price questions use deterministic price helpers rather than generated SQL.

Supported price intents include:

```text
price trend
latest price across stores
latest price at a store
```

## Effective Item Pricing

Price analytics use effective purchase price after item-level discounts.

```text
effective line price
    = gross line price
      + normalized item discount

effective unit price
    = effective line price / quantity
```

Only positive purchase-item observations are treated as price observations.

Returns and refunds are not interpreted as negative prices.

## Product Identity

Version 2 intentionally keeps product identity limited.

Same-store item codes are treated as strong product identifiers when available.

A small explicit canonical registry is currently used for verified aliases such as:

```text
Whole Milk
Andouille Sausage
```

This avoids broad description matching for known ambiguous terms.

Version 2 does not implement:

- automatic cross-store product matching
- fuzzy product matching
- LLM-based product matching
- persistent store-product mappings
- embeddings or RAG product search

Those are intentionally deferred until meaningful multi-store data exists.

## Current Verified Analytics Baseline

Current verified dataset:

```text
803 transactions
635 purchases
168 returns / refunds
$39,888 net spend
```

Examples of verified price analytics:

```text
Whole Milk at Costco
latest effective unit price: $3.00
date: 2026-08-23

Andouille Sausage at Costco
latest effective unit price: $14.99
date: 2026-04-19
```

## Running the Dashboard

```bash
uv run streamlit run app/app.py
```

To expose Streamlit to another device on the same network:

```bash
uv run streamlit run app/app.py --server.address 0.0.0.0
```

## Important Environment Variables

The application uses environment variables rather than committed credentials.

Key variables include:

```text
DATABASE_URL
ANALYTICS_DATABASE_URL
RECEIPT_DB_BACKEND
```

API keys, database URLs, OneDrive credentials, private receipt files, and personal data must never be committed to the repository.

## Version 2 Scope

Version 2 is considered complete when:

- ingestion remains reliable
- historical Costco data is available for analytics
- analytics access remains read-only
- dashboard metrics and item analytics are verified
- effective-price calculations are verified
- natural-language analytics are verified
- price questions route safely
- repository schema and documentation reflect the current system

Future versions may introduce true cross-store product intelligence after enough multi-store receipt history has accumulated.
