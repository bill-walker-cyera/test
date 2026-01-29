# Pendo to Salesforce Sync

This repo contains a small Python CLI to read a table from Pendo via the
aggregation API and upsert the results into Salesforce (SFDC).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Required environment variables

Pendo:
- `PENDO_INTEGRATION_KEY` (preferred) or `PENDO_API_KEY`
- `PENDO_BASE_URL` (optional, defaults to `https://app.pendo.io`)
- `PENDO_REQUEST_TIMEOUT_SECONDS` (optional, defaults to 60)

Salesforce (choose one auth method):
- OAuth/session auth:
  - `SFDC_ACCESS_TOKEN`
  - `SFDC_INSTANCE_URL`
- Username/password auth:
  - `SFDC_USERNAME`
  - `SFDC_PASSWORD`
  - `SFDC_SECURITY_TOKEN`
  - `SFDC_DOMAIN` (optional, defaults to `login`)

Optional:
- `SFDC_API_VERSION` (example: `60.0`)

## Running the sync

```bash
python -m pendo_to_sfdc.cli \
  --query-file path/to/pendo_query.json \
  --mapping-file path/to/mapping.json
```

To validate the mapping before writing to Salesforce, use `--dry-run`.

```bash
python -m pendo_to_sfdc.cli \
  --query-file path/to/pendo_query.json \
  --mapping-file path/to/mapping.json \
  --dry-run
```

## Mapping file format

`mapping.json` tells the tool how to translate Pendo rows into Salesforce
records.

```json
{
  "sfdc_object": "Account",
  "external_id_field": "Pendo_Id__c",
  "results_path": "results",
  "field_map": {
    "visitorId": "Pendo_Visitor_Id__c",
    "accountId": "Pendo_Account_Id__c",
    "metadata.plan": "Plan__c"
  },
  "static_fields": {
    "RecordTypeId": "012xxxxxxxxxxxx"
  },
  "ignore_nulls": true,
  "batch_size": 2000,
  "use_serial": true
}
```

Notes:
- `results_path` is optional. Use it when the Pendo response nests the list of
  rows under a key other than `results`.
- `field_map` keys can use dot paths to access nested Pendo values.
- If Pendo returns rows as arrays, add `"columns": ["col1", "col2"]` to the
  mapping file so the rows can be aligned to names.

## Pendo query file

The query file should be the JSON payload you would send to Pendo's
`/api/v1/aggregation` endpoint. Export it from Pendo Data Explorer or build it
manually.

## Example: Pendo query skeleton

```json
{
  "request": {
    "pipeline": [
      {
        "source": {
          "table": "events"
        }
      },
      {
        "select": {
          "fields": ["visitorId", "accountId", "metadata.plan"]
        }
      }
    ]
  }
}
```
