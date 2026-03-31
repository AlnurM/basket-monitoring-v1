---
phase: 01-infrastructure-and-scraping-engines
plan: 04
subsystem: infra
tags: [docker, railway, playwright, apscheduler, aiogram]

requires:
  - phase: 01-02
    provides: BrowserManager singleton, scraper engines
  - phase: 01-03
    provides: Bot/Dispatcher factory, handlers, middlewares
provides:
  - Application entry point wiring bot + browser + scheduler in single process
  - Startup validation (DB + Playwright + bot token, fail-fast)
  - Docker infrastructure (Dockerfile with MS Playwright base, docker-compose, railway.toml)
  - APScheduler with Asia/Almaty timezone
affects: [phase-02, phase-03, deployment]

tech-stack:
  added: [apscheduler, docker-compose, setuptools]
  patterns: [startup-validation, lifecycle-hooks, single-process-architecture]

key-files:
  created:
    - src/price_spy/__main__.py
    - Dockerfile
    - docker-compose.yml
    - railway.toml
    - .dockerignore

key-decisions:
  - "Microsoft Playwright Docker base image (mcr.microsoft.com/playwright/python:v1.50.0-noble)"
  - "APScheduler reconstructs jobs from code on startup (jobstore deferred to Phase 3)"
  - "Startup validation fail-fast: DB, Playwright, bot token checks before polling"
  - "Pin setuptools<81 for playwright-stealth pkg_resources compatibility"

patterns-established:
  - "Lifecycle hooks: on_startup (browser + scheduler), on_shutdown (cleanup)"
  - "Startup validation: test all dependencies before accepting traffic"
  - "Single process: bot polling + scheduler in same asyncio event loop"

requirements-completed: [INFR-01, INFR-03, INFR-04, INFR-05, INFR-07, SCRP-05, SCRP-08]

duration: 12min
completed: 2026-03-31
---

# Plan 01-04: Entry Point & Infrastructure Summary

**Application entry point wires bot + Playwright browser + APScheduler into a single process with fail-fast startup validation and Docker infrastructure for Railway deployment.**

## What Was Built

1. **`__main__.py`** — Full application entry point: `validate_startup()` tests DB/Playwright/bot token and crashes on failure, `on_startup` launches BrowserManager and APScheduler (Asia/Almaty timezone), `on_shutdown` cleans up, `main()` orchestrates the full lifecycle with aiogram polling.

2. **Dockerfile** — Based on `mcr.microsoft.com/playwright/python:v1.50.0-noble` with uv for dependency management. No separate Playwright install needed (pre-installed in base image).

3. **docker-compose.yml** — Local dev stack: PostgreSQL 16 with healthcheck + bot service with volume mount for live code.

4. **railway.toml** — Dockerfile builder, ON_FAILURE restart policy, no healthcheck endpoint (startup validation handles this).

## Issues Encountered

- **setuptools 82+ removed `pkg_resources`** — `playwright-stealth` depends on `pkg_resources`. Fixed by pinning `setuptools>=75.0,<81` in pyproject.toml.

## Self-Check: PASSED

- [x] `__main__.py` has validate_startup, on_startup, on_shutdown, main, daily_scrape functions
- [x] Dockerfile uses MS Playwright base image
- [x] docker-compose.yml has postgres:16 + bot service
- [x] railway.toml configured for Dockerfile deployment
- [x] All imports resolve correctly
- [x] Human verified: bot starts, responds to /start and /help
