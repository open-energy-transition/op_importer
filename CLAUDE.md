# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`op_importer` is a Textual TUI that bulk-imports work packages from a CSV file into an OpenProject instance through its REST API v3.

## Commands

The environment is managed with pixi (linux-64 only, Python >= 3.13).

```bash
pixi install
pixi run start                      # launch the TUI (console script `op_import`)
pixi run test                       # offline suite, deselects tests marked `live`
pixi run test -m live               # only the live tests, against the server in .env (see below)
pixi run test tests/test_data_model.py::test_work_package_serialization
pre-commit run --all-files          # black + isort (black profile) + flake8 + mypy, line length 120
```

`pre-commit` is not part of the pixi environment. The mypy hook installs pydantic, textual, rich, python-dotenv and pytest (`additional_dependencies`), so calls into these libraries are type-checked; keep their bounds in sync with `pyproject.toml`.

## Configuration

`get_data.py` and `validate.py` each call `load_dotenv()` at import time and read `OPENPROJECT_API_URL` (e.g. `https://host/api/v3`) and `OPENPROJECT_API_KEY` into module-level constants. Auth is HTTP basic with the literal user `apikey`. Changing the environment after import has no effect. Because `.env` is loaded automatically, `pixi run start` needs no wrapper script.

## Tests

`pyproject.toml` sets `addopts = "-m 'not live'"`, so `pixi run test` stays offline. Offline tests that touch the API use the `fake_api` fixture (`tests/conftest.py`). It monkeypatches `requests.get`/`requests.post` and answers by URL suffix. It returns the mutable route-to-JSON dict, so a test edits one route (e.g. `fake_api["/work_packages/form"]`). Collections built with `elements()` carry `count` and `total`, and a route whose JSON has `"_type": "Error"` answers with status 422. Stub only this HTTP boundary, not package functions. pytest-asyncio is not installed, so `tests/test_app.py` drives the TUI from sync tests: a coroutine opens `async with app.run_test(notifications=True) as pilot:` and is passed to `asyncio.run`. Toasts are only mounted with `notifications=True`, and rendering happens asynchronously, so `await pilot.pause()` before asserting on toasts or rendered cells. Validation and ingest run as Textual workers, so `settle()` in `tests/test_app.py` pauses, awaits the app's own workers (`worker.node is app`), and pauses again. Do not call `app.workers.wait_for_complete()` without arguments: the `DirectoryTree`'s `_loader` worker never finishes, so it hangs. An empty list hangs too, because it falls back to all workers.

Tests marked `live` (`test_api.py`, `test_main.py`, `test_validate.py::TestValidateWorkPackage`) call the instance configured in `.env`:

- `test_api.py::test_create_workpackage` creates a real work package in project 3.
- `test_main.py` asserts instance-specific data (project 5 "Other Projects", type 3 "Summary task", priority 8 "Normal").

Run `-m live` only against a disposable local instance. `README.md` describes the Docker setup (OpenProject 16 on `localhost:8080`) and how to restore a database dump into it.

## Architecture

Data flow of one import:

1. `app/main.py` (`OpenProjectImporterApp`): selecting a `.csv` in the directory tree calls `load_file`, which reads it and starts validation at once (there are no Load or Validate buttons). Its headers must include the `WorkPackage` field names `subject,description,status,work_package_type,startDate,dueDate` (`REQUIRED_HEADERS`); the `project` column is optional and defaults to `None`. Selecting a project in the `ListView` sets every row's `project` to that project's ID, overriding the CSV column, and re-validates (`apply_and_validate`). The expected headers, the table's column keys and order, and each row's cells all derive from `WorkPackage.model_fields`; `COLUMN_LABELS` only maps field names to column labels, so a new model field needs a label there. Dates are parsed as `DD/MM/YYYY`. `project`, `status` and `work_package_type` are numeric OpenProject IDs.
2. The `validate_data` worker (`@work(exclusive=True, group="validate")`) runs `op_importer.main(rows)` from `__init__.py` on a copy of the rows in a thread (`asyncio.to_thread`), with a loading overlay on the table. A new file or project selection cancels a running validation and starts a new one. `main` first fetches the known project and type IDs once per run (`validate.KnownIds.fetch()`, two GETs). Then, for each row, it does the following:
   - builds the pydantic `WorkPackage` (`data_model.py`) for local type checks, and turns pydantic errors into `{"field", "message"}` dicts;
   - calls `validate.validate(payload, known_ids)`, which checks that the project and type IDs are in `known_ids`, then POSTs the serialized payload to `/work_packages/form`. OpenProject's `_embedded.validationErrors` become error dicts. `data_model.API_FIELD_NAMES` (derived from the serialization aliases, e.g. `type` -> `work_package_type`) renames their keys to model field names. Attributes without an alias keep their API name. On success, `_embedded.payload` is kept.
   - returns a `ValidationResponseList` whose `validation_errors` and `validation_results` are keyed by row index.
3. The TUI marks invalid cells with a red `*`, using each error's `field` as the DataTable column key (the `WorkPackage` field names). Selecting a marked cell shows its message in the `#editor` TextArea. An error whose `field` has no column (e.g. `priority`) is shown as an error notification with its 1-based row number instead. Ingest is enabled only while `self.results` holds a fully valid run (`update_ingest_button`).
4. Pressing Ingest passes the stored `results` to the `ingest_data` worker and clears `self.results` at once, which disables Ingest and blocks duplicate imports. It also disables the directory tree and the project list (`lock_inputs`) until the worker ends, so no new validation can re-enable Ingest mid-import. The worker POSTs each `validation_results` entry (the payload returned by the API form, not the local model) to `/work_packages` via `get_data.create_workpackage` in a thread. Each failure raises an error toast `Row N: <message>`, and one summary toast `Created n of total work packages.` follows.

Details that span files:

- `WorkPackage` serializes to the API's HAL format through `field_serializer`s: IDs become `{"href": "/api/v3/<resource>/<id>"}`, `description` becomes `{"raw": ..., "format": "markdown"}`, and `work_package_type` is aliased to `type`. Always dump with `model_dump(by_alias=True)`.
- `project` is optional in `WorkPackage`, but `Validate.validate_project_id` rejects `None`, so it is effectively required.
- `validate.Validate` is a base class whose subclasses implement `get_form()`. `Validate`, `GetValidator.select_validator` and `validate()` require a `KnownIds`; none of them fetches IDs. `GetValidator.select_validator` always returns `ValidateWorkPackage`; `ValidateProjectWorkPackage` is unreachable.
- Name clash: `op_importer.main` is the validation function. `op_importer.app.main` is the TUI module, whose `main()` is exported as `op_importer.app.app` (the console script target).
- Importing `op_importer` routes root logging through Textual's `TextualHandler`, so log output does not reach stdout.
- The project selected in the `ListView` overrides the CSV `project` column for every row, and `#project_label` names it. Without a selection the CSV column decides, and a missing column fails validation on `project`.
- The TUI renders all CSV and API data without markup: data-carrying `notify` calls pass `markup=False`, non-empty table cells are `rich.text.Text`, and project names use `Label(..., markup=False)`. Textual and Rich parse plain strings as markup, so tag-like text such as `[EUR]` or `[x]` can vanish and an unmatched closing tag such as `[/x]` crashes the app with `MarkupError`.
- `get_data.py` holds thin `requests` wrappers that return raw `response.json()`. Only the POST helpers also return the status code. `get_projects` and `get_types` go through `get_collection`, which requests `pageSize=MAX_PAGE_SIZE` (1000, the server's `maximumAPIV3PageSize`; the default page holds 20) and raises `ValueError` if the result is still truncated (`count < total`).
