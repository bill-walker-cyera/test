# Pendo NPS to Salesforce Sync

This repo contains a small Node.js script that pulls NPS responses from Pendo
and upserts them into a Salesforce table (custom object).

## Requirements

- Node.js 18+
- A Salesforce Connected App with OAuth credentials
- A Salesforce custom object with an External ID field
- A Pendo Integration Key with access to NPS responses

## Setup

1. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

2. Update `.env` with your credentials and mapping. At minimum:

   - `PENDO_INTEGRATION_KEY`
   - `PENDO_NPS_API_URL` (or `PENDO_NPS_POLL_ID`)
   - `SFDC_CLIENT_ID`
   - `SFDC_CLIENT_SECRET`
   - `SFDC_USERNAME`
   - `SFDC_PASSWORD`
   - `SFDC_SECURITY_TOKEN`
   - `SFDC_OBJECT`
   - `SFDC_EXTERNAL_ID_FIELD`
   - `SFDC_FIELD_MAP`

3. Run the sync:

   ```bash
   npm start
   ```

## Configuration

The script reads a local `.env` file if present. Values already defined in the
environment are not overridden.

### Pendo settings

- `PENDO_INTEGRATION_KEY` (required): Integration key used in the request
  header.
- `PENDO_BASE_URL` (optional, default: `https://app.pendo.io`).
- `PENDO_NPS_API_URL` (recommended): Full API URL to fetch responses.
- `PENDO_NPS_POLL_ID` (optional): If set, the script calls
  `/api/v1/poll/<id>/response`.
- `PENDO_NPS_METHOD` (optional, default: `GET`).
- `PENDO_NPS_BODY` (optional): JSON string used as the request body for
  non-GET requests.
- `PENDO_NPS_RESULTS_PATH` (optional): Dot path to the array of responses in
  the returned JSON (for example `data.responses`).
- `PENDO_EXTERNAL_ID_PATH` (optional, default: `id`): Path used to populate the
  external ID when the mapping does not include it.

### Salesforce settings

- `SFDC_LOGIN_URL` (optional, default: `https://login.salesforce.com`).
- `SFDC_API_VERSION` (optional, default: `60.0`).
- `SFDC_CLIENT_ID`, `SFDC_CLIENT_SECRET` (required).
- `SFDC_USERNAME`, `SFDC_PASSWORD` (required).
- `SFDC_SECURITY_TOKEN` (optional): Appended to the password when present.
- `SFDC_OBJECT` (optional, default: `NPS_Response__c`).
- `SFDC_EXTERNAL_ID_FIELD` (optional, default: `Pendo_Response_Id__c`).
- `SFDC_FIELD_MAP` (required in practice): JSON mapping of Salesforce field
  names to Pendo response paths.
- `SFDC_STATIC_FIELDS` (optional): JSON object of fixed fields to set on every
  record (for example `{"Source__c":"Pendo"}`).
- `SFDC_CONCURRENCY` (optional, default: `5`): Upsert concurrency.

### Example mapping

```json
{
  "Pendo_Response_Id__c": "id",
  "Score__c": "score",
  "Comment__c": "comment",
  "Response_At__c": "createdAt",
  "Visitor_Id__c": "visitor.id",
  "Account_Id__c": "visitor.accountId"
}
```

Make sure the fields in the mapping exist on your Salesforce custom object.
