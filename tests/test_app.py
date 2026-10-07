import asyncio
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import pytest
import requests
from textual.pilot import Pilot
from textual.widgets import Button, Label, ListView, TextArea
from textual.widgets._toast import Toast

from op_importer.app.main import (
    FilteredDirectoryTree,
    OpenProjectImporterApp,
    WorkPackageTable,
)

TEST_CSV = Path(__file__).parent / "fixtures" / "test.csv"
INVALID_HEADERS = Path(__file__).parent / "fixtures" / "invalid_headers.csv"
HEADERS = "subject,description,status,work_package_type,startDate,dueDate"
WITH_PROJECT = f"{HEADERS},project\nTask,,1,3,,,4\n"
WITHOUT_PROJECT = f"{HEADERS}\nTask,,1,3,,\n"
TYPE_ERROR = "Type is not enabled in this project."
PRIORITY_ERROR = "Priority is not set to one of the allowed values."


@dataclass
class Observed:
    first_row: str
    type_cell: str
    toasts: list[str]
    editor: str
    projects: list[str]
    project_cell: str
    ingest_disabled: bool
    inputs_during_ingest: tuple[bool, bool] | None
    inputs_after: tuple[bool, bool]


def gate_posts(monkeypatch: pytest.MonkeyPatch, suffix: str) -> threading.Event:
    gate = threading.Event()
    respond = requests.post

    def gated_post(url: str, **kwargs: Any) -> Any:
        if url.endswith(suffix):
            assert gate.wait(timeout=10)
        return respond(url, **kwargs)

    monkeypatch.setattr(requests, "post", gated_post)
    return gate


@pytest.fixture
def ingest_gate(fake_api: dict[str, dict], monkeypatch: pytest.MonkeyPatch) -> threading.Event:
    return gate_posts(monkeypatch, "/work_packages")


@pytest.fixture
def form_gate(fake_api: dict[str, dict], monkeypatch: pytest.MonkeyPatch) -> threading.Event:
    return gate_posts(monkeypatch, "/work_packages/form")


def select_project(app: OpenProjectImporterApp, index: int) -> None:
    list_view = app.query_one(ListView)
    list_view.index = index
    list_view.action_select_cursor()


def inputs_disabled(app: OpenProjectImporterApp) -> tuple[bool, bool]:
    return app.query_one(FilteredDirectoryTree).disabled, app.query_one(ListView).disabled


async def settle(pilot: Pilot) -> None:
    await pilot.pause()
    app_workers = [worker for worker in pilot.app.workers if worker.node is pilot.app and not worker.is_cancelled]
    await asyncio.gather(*(worker.wait() for worker in app_workers))
    await pilot.pause()


async def run_app(csv: Path, project_index: int | None = None, ingest_gate: threading.Event | None = None) -> Observed:
    app = OpenProjectImporterApp()
    async with app.run_test(notifications=True) as pilot:
        app.load_file(csv)
        await settle(pilot)
        if project_index is not None:
            select_project(app, project_index)
            await settle(pilot)
        inputs_during_ingest: tuple[bool, bool] | None = None
        if ingest_gate is not None:
            app.query_one("#ingest_button", Button).press()
            await pilot.pause()
            inputs_during_ingest = inputs_disabled(app)
            ingest_gate.set()
            await settle(pilot)
        table = app.query_one("#table", WorkPackageTable)
        first_row = table.render_line(1).text
        toasts = [str(toast.render()) for toast in app.query(Toast)]
        table.move_cursor(row=0, column=table.get_column_index("work_package_type"))
        table.action_select_cursor()
        await pilot.pause()
        return Observed(
            first_row=first_row,
            type_cell=str(table.get_cell("0", "work_package_type")),
            toasts=toasts,
            editor=app.query_one("#editor", TextArea).text,
            projects=[str(label.render()) for label in app.query("ListItem > Label").results(Label)],
            project_cell=str(table.get_cell("0", "project")),
            ingest_disabled=app.query_one("#ingest_button", Button).disabled,
            inputs_during_ingest=inputs_during_ingest,
            inputs_after=inputs_disabled(app),
        )


def validate_with_errors(fake_api: dict[str, dict], priority_message: str) -> Observed:
    fake_api["/work_packages/form"]["_embedded"]["validationErrors"] = {
        "type": {"message": TYPE_ERROR},
        "priority": {"message": priority_message},
    }
    return asyncio.run(run_app(TEST_CSV))


@pytest.mark.parametrize("message", [PRIORITY_ERROR, "Budget [EUR] can't be blank.", "Budget [/EUR] can't be blank."])
def test_error_without_column_is_notified_verbatim(fake_api: dict[str, dict], message: str) -> None:
    assert f"Validation Error\nRow 1, priority: {message}" in validate_with_errors(fake_api, message).toasts


def test_type_error_marks_cell_and_shows_message_when_selected(fake_api: dict[str, dict]) -> None:
    observed = validate_with_errors(fake_api, PRIORITY_ERROR)

    assert (observed.type_cell, observed.editor) == ("*", TYPE_ERROR)


@pytest.mark.parametrize("text", ["Fix [x] bug", "Fix [/x] bug"])
def test_csv_and_api_values_render_verbatim(fake_api: dict[str, dict], tmp_path: Path, text: str) -> None:
    fake_api["/projects"]["_embedded"]["elements"][0]["name"] = text
    csv = tmp_path / "work_packages.csv"
    csv.write_text(f"subject,description,project,status,work_package_type,startDate,dueDate\n{text},,4,1,3,,\n")

    observed = asyncio.run(run_app(csv))

    assert text in observed.first_row
    assert observed.projects == [text, "Project 5"]


@pytest.mark.parametrize(
    ("csv_text", "project_index", "project_cell", "ingest_disabled"),
    [
        (WITH_PROJECT, None, "4", False),
        (WITHOUT_PROJECT, None, "*", True),
        (WITHOUT_PROJECT, 1, "5", False),
        (WITH_PROJECT, 1, "5", False),
    ],
    ids=["csv", "no-project", "no-project-selected", "csv-overridden"],
)
def test_selected_project_overrides_csv_column(
    fake_api: dict[str, dict],
    tmp_path: Path,
    csv_text: str,
    project_index: int | None,
    project_cell: str,
    ingest_disabled: bool,
) -> None:
    csv = tmp_path / "work_packages.csv"
    csv.write_text(csv_text)

    observed = asyncio.run(run_app(csv, project_index))

    assert (observed.project_cell, observed.ingest_disabled) == (project_cell, ingest_disabled)


@pytest.mark.parametrize(
    ("response", "toasts"),
    [
        ({}, {"Ingestion\nCreated 3 of 3 work packages."}),
        (
            {"_type": "Error", "message": "Subject is too long."},
            {"Ingestion Error\nRow 1: Subject is too long.", "Ingestion\nCreated 0 of 3 work packages."},
        ),
    ],
)
def test_ingest_locks_inputs_and_reports_outcome(
    fake_api: dict[str, dict], ingest_gate: threading.Event, response: dict, toasts: set[str]
) -> None:
    fake_api["/work_packages"] = response

    observed = asyncio.run(run_app(TEST_CSV, ingest_gate=ingest_gate))

    assert toasts <= set(observed.toasts)
    assert observed.ingest_disabled
    assert (observed.inputs_during_ingest, observed.inputs_after) == ((True, True), (False, False))


SUPERSEDE: dict[str, Callable[[OpenProjectImporterApp], None]] = {
    "invalid-headers": lambda app: app.load_file(INVALID_HEADERS),
    "unknown-project": lambda app: select_project(app, 1),
}


@pytest.mark.parametrize("running", [True, False], ids=["running", "settled"])
@pytest.mark.parametrize("supersede", SUPERSEDE.values(), ids=SUPERSEDE.keys())
def test_superseded_validation_cannot_enable_ingest(
    fake_api: dict[str, dict],
    form_gate: threading.Event,
    supersede: Callable[[OpenProjectImporterApp], None],
    running: bool,
) -> None:
    async def scenario() -> tuple[bool, bool]:
        app = OpenProjectImporterApp()
        async with app.run_test(notifications=True) as pilot:
            fake_api["/projects"] = {
                "_embedded": {"elements": [{"id": 4, "name": "Project 4"}]},
                "count": 1,
                "total": 1,
            }
            app.load_file(TEST_CSV)
            await pilot.pause()
            if not running:
                form_gate.set()
                await settle(pilot)
            supersede(app)
            await pilot.pause()
            form_gate.set()
            await settle(pilot)
            return app.query_one("#ingest_button", Button).disabled, app.query_one("#table", WorkPackageTable).loading

    assert asyncio.run(scenario()) == (True, False)
