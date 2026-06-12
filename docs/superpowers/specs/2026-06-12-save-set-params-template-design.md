# Save Set Params Template Design

## Goal

When a successful parameter-read response is received, persist the actual returned parameters into `src/json/setParams.json` by replacing only `params.data`.

## Behavior

- Keep the existing UI behavior: the editor is filled with a parameter-write JSON command based on `setParams.json`.
- Add a backend API that accepts the returned parameter object and writes it into `setParams.json`.
- Preserve the command envelope in `setParams.json`, including `moduleType`, `eventType`, `deviceIdx`, `deviceIp`, `eventTime`, `operationCommand`, `paramType`, and `engineName`.
- Format the saved JSON with indentation and UTF-8 text.
- If saving fails, log the failure in the terminal panel without clearing the editor contents.

## Architecture

The frontend remains responsible for detecting successful parameter-read responses. The backend owns disk writes so browser code never writes files directly. `server.py` will expose one narrow POST endpoint for updating `setParams.json`; `App.vue` will call it from `fillSetParamsFromParamReadResponse`.

## Tests

- Backend test: the update helper replaces only `params.data` and preserves outer fields.
- Backend API test: `POST /api/json/update-set-params` writes the file and returns JSON success.
- Frontend architecture test: `App.vue` calls the new endpoint when parameter-read data is applied.
