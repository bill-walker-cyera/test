const fs = require("node:fs");
const path = require("node:path");
const { URL, URLSearchParams } = require("node:url");

const DEFAULT_PENDO_BASE_URL = "https://app.pendo.io";
const DEFAULT_SFDC_LOGIN_URL = "https://login.salesforce.com";
const DEFAULT_SFDC_API_VERSION = "60.0";

function loadDotEnv(filePath) {
  if (!fs.existsSync(filePath)) {
    return;
  }

  const contents = fs.readFileSync(filePath, "utf8");
  for (const line of contents.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }

    const equalsIndex = trimmed.indexOf("=");
    if (equalsIndex === -1) {
      continue;
    }

    const key = trimmed.slice(0, equalsIndex).trim();
    if (!key) {
      continue;
    }

    let value = trimmed.slice(equalsIndex + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }

    if (process.env[key] === undefined) {
      process.env[key] = value;
    }
  }
}

function parseJsonEnv(name, fallback) {
  const raw = process.env[name];
  if (!raw) {
    return fallback;
  }

  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new Error(`Invalid JSON in ${name}: ${error.message}`);
  }
}

function parsePositiveInt(raw, fallback) {
  if (!raw) {
    return fallback;
  }

  const parsed = Number.parseInt(raw, 10);
  if (Number.isNaN(parsed) || parsed <= 0) {
    return fallback;
  }

  return parsed;
}

function requireEnv(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

function getByPath(value, pathExpression) {
  if (!pathExpression) {
    return undefined;
  }

  return pathExpression.split(".").reduce((acc, key) => {
    if (acc === null || acc === undefined) {
      return undefined;
    }
    return acc[key];
  }, value);
}

function normalizePendoResponses(payload, resultsPath) {
  if (!payload) {
    return [];
  }

  if (Array.isArray(payload)) {
    return payload;
  }

  if (resultsPath) {
    const resolved = getByPath(payload, resultsPath);
    if (Array.isArray(resolved)) {
      return resolved;
    }
    throw new Error(
      `PENDO_NPS_RESULTS_PATH did not resolve to an array: ${resultsPath}`
    );
  }

  const candidates = ["responses", "results", "data"];
  for (const key of candidates) {
    if (Array.isArray(payload[key])) {
      return payload[key];
    }
  }

  throw new Error(
    "Unable to locate a response array. Set PENDO_NPS_RESULTS_PATH."
  );
}

function buildConfig() {
  loadDotEnv(path.join(process.cwd(), ".env"));

  const pendoIntegrationKey = requireEnv("PENDO_INTEGRATION_KEY");
  const pendoBaseUrl = process.env.PENDO_BASE_URL || DEFAULT_PENDO_BASE_URL;
  const pendoNpsApiUrl = process.env.PENDO_NPS_API_URL || "";
  const pendoPollId = process.env.PENDO_NPS_POLL_ID || "";
  const pendoMethod = (process.env.PENDO_NPS_METHOD || "GET").toUpperCase();
  const pendoResultsPath = process.env.PENDO_NPS_RESULTS_PATH || "";
  const pendoExternalIdPath = process.env.PENDO_EXTERNAL_ID_PATH || "id";
  const pendoBody = parseJsonEnv("PENDO_NPS_BODY", null);

  const sfdcLoginUrl = process.env.SFDC_LOGIN_URL || DEFAULT_SFDC_LOGIN_URL;
  const sfdcApiVersion = process.env.SFDC_API_VERSION || DEFAULT_SFDC_API_VERSION;
  const sfdcObject = process.env.SFDC_OBJECT || "NPS_Response__c";
  const sfdcExternalIdField =
    process.env.SFDC_EXTERNAL_ID_FIELD || "Pendo_Response_Id__c";

  const defaultFieldMap = {
    [sfdcExternalIdField]: pendoExternalIdPath,
    Score__c: "score",
    Comment__c: "comment",
    Response_At__c: "createdAt",
    Visitor_Id__c: "visitor.id",
    Account_Id__c: "visitor.accountId",
  };

  const sfdcFieldMap = parseJsonEnv("SFDC_FIELD_MAP", defaultFieldMap);
  const sfdcStaticFields = parseJsonEnv("SFDC_STATIC_FIELDS", {});

  const sfdcConcurrency = parsePositiveInt(process.env.SFDC_CONCURRENCY, 5);

  return {
    pendoIntegrationKey,
    pendoBaseUrl,
    pendoNpsApiUrl,
    pendoPollId,
    pendoMethod,
    pendoResultsPath,
    pendoExternalIdPath,
    pendoBody,
    sfdcLoginUrl,
    sfdcApiVersion,
    sfdcObject,
    sfdcExternalIdField,
    sfdcFieldMap,
    sfdcStaticFields,
    sfdcConcurrency,
    sfdcClientId: requireEnv("SFDC_CLIENT_ID"),
    sfdcClientSecret: requireEnv("SFDC_CLIENT_SECRET"),
    sfdcUsername: requireEnv("SFDC_USERNAME"),
    sfdcPassword: requireEnv("SFDC_PASSWORD"),
    sfdcSecurityToken: process.env.SFDC_SECURITY_TOKEN || "",
  };
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const text = await response.text();
  let payload;

  if (text) {
    try {
      payload = JSON.parse(text);
    } catch (error) {
      throw new Error(
        `Failed to parse JSON response (${response.status}): ${text}`
      );
    }
  }

  if (!response.ok) {
    const details =
      payload?.error_description ||
      payload?.message ||
      payload?.error ||
      text ||
      response.statusText;
    throw new Error(`Request failed (${response.status}): ${details}`);
  }

  return payload;
}

async function fetchPendoResponses(config) {
  const endpoint =
    config.pendoNpsApiUrl ||
    (config.pendoPollId
      ? new URL(
          `/api/v1/poll/${config.pendoPollId}/response`,
          config.pendoBaseUrl
        ).toString()
      : "");

  if (!endpoint) {
    throw new Error("Set PENDO_NPS_API_URL or PENDO_NPS_POLL_ID.");
  }

  const headers = {
    "x-pendo-integration-key": config.pendoIntegrationKey,
  };

  const options = {
    method: config.pendoMethod,
    headers,
  };

  if (config.pendoMethod !== "GET") {
    headers["content-type"] = "application/json";
    if (config.pendoBody) {
      options.body = JSON.stringify(config.pendoBody);
    }
  }

  const payload = await fetchJson(endpoint, options);
  return normalizePendoResponses(payload, config.pendoResultsPath);
}

function buildSalesforceRecord(response, config) {
  const record = { ...config.sfdcStaticFields };

  for (const [field, pathExpression] of Object.entries(
    config.sfdcFieldMap
  )) {
    const value = getByPath(response, pathExpression);
    if (value !== undefined) {
      record[field] = value;
    }
  }

  if (record[config.sfdcExternalIdField] === undefined) {
    const fallback = getByPath(response, config.pendoExternalIdPath);
    if (fallback !== undefined) {
      record[config.sfdcExternalIdField] = fallback;
    }
  }

  return record;
}

function buildSalesforceRecords(responses, config) {
  const records = [];
  let skipped = 0;

  for (const response of responses) {
    const record = buildSalesforceRecord(response, config);
    const externalId = record[config.sfdcExternalIdField];
    if (externalId === undefined || externalId === null || externalId === "") {
      skipped += 1;
      continue;
    }
    records.push(record);
  }

  if (skipped > 0) {
    console.warn(`Skipped ${skipped} responses missing external id.`);
  }

  return records;
}

async function authenticateSalesforce(config) {
  const url = new URL("/services/oauth2/token", config.sfdcLoginUrl);
  const body = new URLSearchParams({
    grant_type: "password",
    client_id: config.sfdcClientId,
    client_secret: config.sfdcClientSecret,
    username: config.sfdcUsername,
    password: `${config.sfdcPassword}${config.sfdcSecurityToken}`,
  });

  const payload = await fetchJson(url.toString(), {
    method: "POST",
    headers: {
      "content-type": "application/x-www-form-urlencoded",
    },
    body,
  });

  if (!payload?.access_token || !payload?.instance_url) {
    throw new Error("Salesforce auth did not return access_token.");
  }

  return {
    accessToken: payload.access_token,
    instanceUrl: payload.instance_url,
  };
}

async function upsertSalesforceRecord(config, auth, record) {
  const externalIdValue = record[config.sfdcExternalIdField];
  const endpoint = new URL(
    `/services/data/v${config.sfdcApiVersion}/sobjects/${config.sfdcObject}/${
      config.sfdcExternalIdField
    }/${encodeURIComponent(String(externalIdValue))}`,
    auth.instanceUrl
  );

  const response = await fetch(endpoint.toString(), {
    method: "PATCH",
    headers: {
      authorization: `Bearer ${auth.accessToken}`,
      "content-type": "application/json",
    },
    body: JSON.stringify(record),
  });

  if (response.ok) {
    return { ok: true };
  }

  const text = await response.text();
  return { ok: false, error: text || response.statusText };
}

async function upsertSalesforceRecords(config, auth, records) {
  const results = {
    success: 0,
    failure: 0,
  };

  for (let i = 0; i < records.length; i += config.sfdcConcurrency) {
    const slice = records.slice(i, i + config.sfdcConcurrency);
    const batchResults = await Promise.all(
      slice.map((record) => upsertSalesforceRecord(config, auth, record))
    );

    for (const result of batchResults) {
      if (result.ok) {
        results.success += 1;
      } else {
        results.failure += 1;
        console.warn(`Salesforce upsert failed: ${result.error}`);
      }
    }
  }

  return results;
}

async function main() {
  const config = buildConfig();

  console.log("Fetching Pendo NPS responses...");
  const responses = await fetchPendoResponses(config);
  console.log(`Fetched ${responses.length} responses.`);

  const records = buildSalesforceRecords(responses, config);
  if (records.length === 0) {
    console.log("No records to send to Salesforce.");
    return;
  }

  console.log(`Upserting ${records.length} records into Salesforce...`);
  const auth = await authenticateSalesforce(config);
  const result = await upsertSalesforceRecords(config, auth, records);

  console.log(
    `Salesforce upsert complete. Success: ${result.success}, Failure: ${result.failure}`
  );

  if (result.failure > 0) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error(`Sync failed: ${error.message}`);
  process.exitCode = 1;
});
