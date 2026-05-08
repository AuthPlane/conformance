# Authplane Conformance Catalog

Language-neutral conformance catalog for Authplane OAuth SDK implementations. This repository defines *what* a conforming SDK must do; each SDK translates the catalog into native tests and produces a report in the shape described below.

## What This Is

A YAML catalog (`oauth-sdk-conformance-catalog.yaml`) of **behavioral test cases** covering the OAuth 2.1 RFCs that Authplane SDKs must implement. Each case specifies setup, stimulus, expected outcome, and rationale — but not language-specific test code.

The catalog is the single source of truth. Test assertions that are not backed by a catalog case — or catalog cases that are not backed by a test — are alignment failures.

## Standards in Scope

The authoritative list lives in `standards_in_scope` at the top of the catalog YAML.

| RFC | Topic |
|-----|-------|
| RFC 3986 | URI generic syntax (htu normalization) |
| RFC 6749 | OAuth 2.0 token endpoint, client auth, error semantics |
| RFC 6750 | Bearer token usage |
| RFC 7009 | Token revocation |
| RFC 7519 | JSON Web Token (JWT) core |
| RFC 7662 | Token introspection |
| RFC 8414 | Authorization server metadata discovery |
| RFC 8693 | Token exchange |
| RFC 8707 | Resource indicators |
| RFC 8725 | JWT best current practices |
| RFC 9068 | JWT access token profile |
| RFC 9110 | HTTP semantics |
| RFC 9449 | DPoP |
| RFC 9728 | Protected resource metadata |

## Case Schema

```yaml
cases:
  - id: "rfc9068-typ-must-be-at-jwt"
    title: "Reject JWTs whose typ is not at+jwt"
    standard_refs: ["RFC9068", "RFC8725"]
    surface: "sdk-verifier.jwt"
    priority: "critical"
    requirement_summary: "The token type MUST be at+jwt."
    setup:
      token_header:
        typ: "JWT"
    stimulus:
      operation: "verifier.verify"
    expected:
      outcome: "reject"
      error_category: "invalid_claims"
    rationale: "Prevents confusion with ID tokens or generic JWTs."
```

Required fields on every case (enforced by `case_fields.required` in the YAML):

| Field | Meaning |
|---|---|
| `id` | Stable identifier shared across all SDK implementations. Never renumbered. |
| `title` | One-line human-readable summary. |
| `standard_refs` | List of RFC IDs that govern the case. Each must appear in `standards_in_scope`. |
| `surface` | SDK component under test (e.g. `sdk-verifier.jwt`, `sdk-client.introspection`). |
| `priority` | `critical` / `high` / `medium` / `low`. |
| `requirement_summary` | Normative requirement in plain English. |
| `setup` | Preconditions, fixtures, token shape, server config. |
| `stimulus` | The operation being exercised. |
| `expected` | Outcome and, where relevant, error category. |
| `rationale` | Why the requirement matters. |

## Implementing a Conformance Suite

An SDK consumes the catalog by:

1. **Loading** `oauth-sdk-conformance-catalog.yaml` (git submodule, vendored copy, or path via env var — the SDK's choice).
2. **Registering one test per case.** Each test is bound to a `case_id` so the runner knows which catalog entry it satisfies (e.g. via a `@conformance("case-id")` decorator, a `conformanceCase("case-id", ...)` wrapper, or equivalent).
3. **Verifying alignment** as part of the suite:
   - Every case in the catalog has a registered test.
   - Every registered test maps to a known case id.
   - Either direction missing is a failure.
4. **Generating a report** (see below) after the run.

### Handling Unsupported Cases

An SDK that cannot (or chooses not to) implement a case MUST still register a test for it and emit it in the report as `status: "skipped"` with a human-readable reason. The reason goes in the per-case `coverage.note` field; `coverage.level` distinguishes partial coverage from none. This keeps the catalog authoritative — readers can tell whether a case is green, red, or consciously deferred, and why.

Do **not** silently omit cases. A missing case is treated as `not_run` and fails alignment.

## Report Format

Every SDK writes a `conformance-report.json` after its conformance suite runs. Shape:

```json
{
  "catalog_id": "oauth-sdk-conformance-catalog",
  "catalog_version": "2026-04-22",
  "implementation": {
    "name": "authplane-<sdk-id>",
    "version": "1.2.3",
    "language": "python"
  },
  "runner": {
    "tool": "pytest",
    "exit_status": 0
  },
  "summary": {
    "total": 111,
    "passed": 105,
    "failed": 0,
    "skipped": 6,
    "not_run": 0
  },
  "cases": [
    {
      "case_id": "rfc9068-typ-must-be-at-jwt",
      "status": "passed",
      "coverage": { "level": "full" }
    },
    {
      "case_id": "rfc9449-dpop-inbound-nonce-must-be-validated-when-required",
      "status": "skipped",
      "coverage": {
        "level": "none",
        "note": "Not implemented: SDK lacks server-side nonce issuance."
      }
    },
    {
      "case_id": "rfc8414-issuer-must-match-configured-issuer",
      "status": "failed",
      "coverage": { "level": "full" },
      "failure": {
        "message": "AssertionError: expected issuer mismatch to raise"
      }
    }
  ]
}
```

### Field Contract

Top-level:

| Field | Type | Notes |
|---|---|---|
| `catalog_id` | string | Must equal the catalog's top-level `catalog_id`. |
| `catalog_version` | string | Must equal the catalog's `catalog_version` at run time. |
| `implementation.name` | string | Package / module identifier. |
| `implementation.version` | string | Semver of the SDK being tested. |
| `implementation.language` | string | `python`, `typescript`, `go`, `java`, etc. |
| `runner.tool` | string | Test runner used (`pytest`, `vitest`, `go test`, ...). |
| `runner.exit_status` | number | Non-zero on any failure. |
| `summary` | object | Aggregated counts; `total` MUST equal `cases.length`. |
| `cases` | array | Ordered to match the catalog. |

Per case:

| Field | Type | Notes |
|---|---|---|
| `case_id` | string | Matches a catalog `id`. |
| `status` | enum | `passed` / `failed` / `skipped` / `not_run`. |
| `coverage.level` | enum | `full` / `partial` / `none`. |
| `coverage.gaps` | array (optional) | Catalog paths not covered under partial. |
| `coverage.note` | string (optional) | Required for `skipped` cases: the reason. |
| `failure` | object (optional) | Present only when `status === "failed"`. Implementation-defined fields (e.g. `message`, `stack`). |

SDKs MAY include additional fields (test nodeid, timestamps, uncatalogued test summaries) as long as the contract above is preserved.

### Status Vocabulary

- `passed` — executed, all assertions succeeded.
- `failed` — executed, assertions or code failed.
- `skipped` — intentionally not exercised. `coverage.note` MUST explain why (e.g. `"unsupported: feature not exposed by this SDK"`).
- `not_run` — a catalog case exists but no test ran for it. This is an alignment bug in the SDK, not an acceptable state.

## Versioning

The catalog version is `catalog_version` at the top of the YAML. Bump it whenever a case is added, removed, or its semantics change. Reports reference this value so a report can be matched to the exact catalog revision it was run against.

## Contributing

New cases go in `oauth-sdk-conformance-catalog.yaml` following the existing format. A new case must:

1. Declare every RFC it references in `standard_refs` (and those RFCs must appear in `standards_in_scope`).
2. Be implementable — setup / stimulus / expected must be concrete enough to test without reading external context.
3. Bump `catalog_version`.

## License

Apache-2.0 — see [LICENSE](LICENSE).
