# Save Set Params Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist successful parameter-read data into `src/json/setParams.json` by replacing only `params.data`.

**Architecture:** Add a small backend helper and HTTP endpoint in `server.py` for safe JSON file updates. Call the endpoint from `App.vue` after the existing editor fill logic succeeds, and log save success or failure.

**Tech Stack:** Python standard library HTTP handling, Vue 3, existing Node architecture test.

---

### Task 1: Backend Persistence Endpoint

**Files:**
- Modify: `tests/test_server.py`
- Modify: `src/server.py`

- [ ] **Step 1: Write failing tests**

Add tests for a helper that updates only `params.data`, and for `POST /api/json/update-set-params`.

- [ ] **Step 2: Verify RED**

Run: `python -m unittest tests.test_server`

Expected: failure because the helper and endpoint do not exist yet.

- [ ] **Step 3: Implement minimal backend code**

Add `update_set_params_template(received_data, template_path=None)` and route `POST /api/json/update-set-params` inside `build_http_response`.

- [ ] **Step 4: Verify GREEN**

Run: `python -m unittest tests.test_server`

Expected: all server tests pass.

### Task 2: Frontend Save Call

**Files:**
- Modify: `tests/test_frontend.js`
- Modify: `src/frontend/src/App.vue`

- [ ] **Step 1: Write failing frontend assertions**

Assert that `App.vue` references `/api/json/update-set-params` and has a save helper.

- [ ] **Step 2: Verify RED**

Run: `npm test`

Expected: failure because the frontend does not call the endpoint yet.

- [ ] **Step 3: Implement minimal frontend code**

Add a JSON POST helper and call it from `fillSetParamsFromParamReadResponse` after `latestParamReadData` is set.

- [ ] **Step 4: Verify GREEN**

Run: `npm test`

Expected: frontend architecture test passes.

### Task 3: Final Verification

**Files:**
- No code changes.

- [ ] **Step 1: Run all tests**

Run: `python -m unittest tests.test_server`

Run: `npm test`

- [ ] **Step 2: Build frontend**

Run: `npm run build`

Expected: build exits with code 0.
