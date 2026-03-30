# Phase 1: Infrastructure and Scraping Engines - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-30
**Phase:** 01-infrastructure-and-scraping-engines
**Areas discussed:** Scraper strategy, i18n architecture, Error reporting, Deployment validation

---

## Scraper Strategy

### Primary scraping approach for Arbuz.kz and Magnum.kz

| Option | Description | Selected |
|--------|-------------|----------|
| DOM selectors first | Start with CSS selectors (reliable baseline), add API interception later as optimization | |
| API interception first | Intercept XHR/fetch responses during page load to find JSON APIs. Fall back to DOM only if no API found | |
| Hybrid from day 1 | Attempt API interception, but always have DOM selectors as fallback in the same scrape cycle | ✓ |

**User's choice:** Hybrid from day 1
**Notes:** User wants both approaches available simultaneously in the same scrape cycle.

### DOM selector discovery approach

| Option | Description | Selected |
|--------|-------------|----------|
| Hardcoded selectors | Research selectors manually, hardcode them. Simple but breaks on site changes | |
| Multi-selector fallback | Try multiple candidate selectors per field (e.g., 3 options for price). More resilient | |
| You decide | Claude picks the best approach based on what the sites actually look like | ✓ |

**User's choice:** You decide (Claude's discretion)

### Kaspi.kz HTML parser

| Option | Description | Selected |
|--------|-------------|----------|
| selectolax (fast) | Lexbor backend, fastest Python HTML parser. Research confirmed it works for SSR | |
| BeautifulSoup (safe) | More mature, better error handling, slightly slower | |
| You decide | Claude picks based on Kaspi's actual HTML structure | ✓ |

**User's choice:** You decide (Claude's discretion)

### Anti-bot evasion aggressiveness

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal (stealth + UA) | playwright-stealth plugin + UA rotation. Start simple, escalate if blocked | |
| Full evasion suite | Stealth + random delays + viewport randomization + cookie persistence + proxy support | ✓ |
| You decide | Claude calibrates based on what Arbuz/Magnum actually detect | |

**User's choice:** Full evasion suite

---

## i18n Architecture

### Bilingual message structure

| Option | Description | Selected |
|--------|-------------|----------|
| Fluent (.ftl files) | Mozilla's Fluent format. Rich pluralization, gender, number formatting | |
| JSON dictionaries | Simple key-value JSON per language. Easy to maintain, common in aiogram projects | |
| gettext (.po files) | Industry standard for Python i18n. Mature tooling. aiogram has built-in gettext support | |
| You decide | Claude picks the best approach for aiogram 3 | ✓ |

**User's choice:** You decide (Claude's discretion)

### Default language before selection

| Option | Description | Selected |
|--------|-------------|----------|
| Russian | Primary audience is Almaty — Russian makes sense as default | |
| English | International default, user switches to Russian if needed | |
| Ask on /start | Force language selection before anything else | ✓ |

**User's choice:** Ask on /start — force selection before proceeding

---

## Error Reporting

### Scrape failure user messaging

| Option | Description | Selected |
|--------|-------------|----------|
| Brief warning | "Could not get price for [product name]" — no technical details | |
| Detailed diagnostic | "[Product] failed: timeout after 30s on arbuz.kz" — helps debug | ✓ |
| Tiered by audience | Brief for regular users, detailed in a /debug command for admin | |

**User's choice:** Detailed diagnostic for all users

### Retry visibility

| Option | Description | Selected |
|--------|-------------|----------|
| Silent retries | Retry 3 times silently, only report final failure | ✓ |
| Show retry progress | "Retrying [product]... (attempt 2/3)" — transparent but noisy | |
| You decide | Claude picks based on context | |

**User's choice:** Silent retries

### Bulk failure handling

| Option | Description | Selected |
|--------|-------------|----------|
| Individual per item | List each failed item separately in the report | ✓ |
| Grouped summary | "5 items from Arbuz.kz unavailable (site may be down)" — less noise | |
| You decide | Claude picks the best approach | |

**User's choice:** Individual per item — even when site-wide failure

---

## Deployment Validation

### Railway deployment validation approach

| Option | Description | Selected |
|--------|-------------|----------|
| Health endpoint + smoke test | Add /health HTTP endpoint, manual smoke test via Telegram | |
| Full startup validation | On boot: verify DB, Playwright, bot token. Fail fast if any check fails | ✓ |
| You decide | Claude designs the deployment validation strategy | |

**User's choice:** Full startup validation with fail-fast

### Docker base image

| Option | Description | Selected |
|--------|-------------|----------|
| python:3.12-slim + manual deps | As in spec — smaller but must install Chromium deps manually | |
| mcr.microsoft.com/playwright/python | Microsoft's official image. Larger but guaranteed compatible | |
| You decide | Claude picks based on Railway constraints | ✓ |

**User's choice:** You decide (Claude's discretion)

### Local development setup

| Option | Description | Selected |
|--------|-------------|----------|
| Local dev without Docker | Run bot.main directly with local PostgreSQL and Playwright | |
| Docker-only | Always run via Docker Compose locally | |
| Both supported | Docker Compose for full stack, but also runnable directly for faster dev | ✓ |

**User's choice:** Both supported — Docker Compose AND direct local run

---

## Claude's Discretion

- Selector discovery approach (hardcoded vs multi-selector fallback)
- Kaspi.kz HTML parser (selectolax vs BeautifulSoup)
- i18n library for aiogram 3 (gettext vs JSON vs Fluent)
- Docker base image (python:3.12-slim vs Microsoft Playwright image)

## Deferred Ideas

None — discussion stayed within phase scope
