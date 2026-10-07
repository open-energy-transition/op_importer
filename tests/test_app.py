import asyncio
from dataclasses import dataclass
from pathlib import Path

import pytest
from textual.widgets import Label, TextArea
from textual.widgets._toast import Toast

from op_importer.app.main import OpenProjectImporterApp, WorkPackageTable

TEST_CSV = Path(__file__).parent / "fixtures" / "test.csv"
TYPE_ERROR = "Type is not enabled in this project."
PRIORITY_ERROR = "Priority is not set to one of the allowed values."


@dataclass
class Observed:
    first_row: str
    type_cell: str
    toasts: list[str]
    editor: str
    projects: list[str]


async def run_app(csv: Path) -> Observed:
    app = OpenProjectImporterApp()
    async with app.run_test(notifications=True) as pilot:
        app.file = csv
        app.load_selected_file()
        app.validate_data()
        await pilot.pause()
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
    assert observed.projects == [text]
