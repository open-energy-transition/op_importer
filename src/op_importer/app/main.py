import asyncio
import sys
from csv import QUOTE_NOTNULL, DictReader
from datetime import datetime
from pathlib import Path
from typing import Iterable

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    DataTable,
    DirectoryTree,
    Footer,
    Header,
    Label,
    ListItem,
    ListView,
    Rule,
    TextArea,
)

from op_importer import main as load_data
from op_importer.data_model import ValidationResponseList, WorkPackage
from op_importer.get_data import (
    create_workpackage,
    get_projects,
    get_roles,
    get_statuses,
    get_types,
    get_users,
    get_work_packages,
)

COLUMN_LABELS: dict[str, str] = {
    "subject": "Subject",
    "description": "Description",
    "project": "Project",
    "work_package_type": "Type",
    "status": "Status",
    "startDate": "Start Date",
    "dueDate": "Due Date",
}

REQUIRED_HEADERS = set(WorkPackage.model_fields) - {"project"}

CsvRow = dict[str, str | datetime | None]


def table_cell(value: str | datetime | None) -> Text | None:
    if isinstance(value, datetime):
        return Text(value.date().isoformat())
    return None if value is None else Text(value)


class FilteredDirectoryTree(DirectoryTree):
    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        for path in paths:
            if path.is_file() and path.name.endswith(".csv"):
                yield path
            elif path.is_dir():
                yield path


class WorkPackageTable(DataTable):

    def on_mount(self) -> None:
        self.add_columns(*((COLUMN_LABELS[field], field) for field in WorkPackage.model_fields))


class OpenProjectImporterApp(App[int]):
    """A Textual app for importing data into OpenProject."""

    TITLE = "OpenProject Importer"
    SUB_TITLE = "Validate and Ingest data into OpenProject"

    def get_data(self) -> None:
        self.users = get_users()
        self.roles = get_roles()
        self.projects = get_projects()
        self.work_packages = get_work_packages()
        self.types = get_types()
        self.statuses = get_statuses()

    def get_project_names(self) -> list[str]:
        return [project["name"] for project in self.projects["_embedded"]["elements"]]

    def compose(self) -> ComposeResult:
        self.data: list[CsvRow] | None = None
        self.results: ValidationResponseList | None = None
        self.project: dict | None = None
        self.get_data()
        yield Header()
        yield Label("Select a CSV file to import:")
        yield Horizontal(FilteredDirectoryTree("./"), WorkPackageTable(id="table"))
        yield Rule()
        project_items = [ListItem(Label(name, markup=False)) for name in self.get_project_names()]
        yield Label("Select a project to import into:", id="project_label")
        yield Horizontal(
            ListView(*project_items),
            Vertical(
                TextArea("", read_only=True, id="editor"),
                Button("Ingest", id="ingest_button", variant="success", disabled=True),
            ),
        )

        yield Footer()

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        self.load_file(event.path)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.project = self.projects["_embedded"]["elements"][event.index]
        label = Text(f"Importing into: {self.project['name']} (ID {self.project['id']})")
        self.query_one("#project_label", Label).update(label)
        if self.data is not None:
            self.apply_and_validate()

    def lock_inputs(self, locked: bool) -> None:
        self.query_one(FilteredDirectoryTree).disabled = locked
        self.query_one(ListView).disabled = locked

    def update_ingest_button(self) -> None:
        self.query_one("#ingest_button", Button).disabled = self.results is None or not self.results.validation_status

    def load_file(self, path: Path) -> None:
        self.workers.cancel_group(self, "validate")
        self.data = None
        self.results = None
        self.update_ingest_button()
        table = self.query_one("#table", WorkPackageTable)
        table.loading = False
        table.clear()
        self.query_one("#editor", TextArea).clear()

        with open(path, "r") as f:
            reader = DictReader(f, quoting=QUOTE_NOTNULL)
            if not REQUIRED_HEADERS.issubset(reader.fieldnames or ()):
                self.notify(
                    "Invalid CSV format. Please ensure the file has the correct headers.",
                    title="CSV Format Error",
                    severity="error",
                )
                return

            data = list(reader)
        for item in data:
            item.setdefault("project", None)
            if item["startDate"]:
                item["startDate"] = datetime.strptime(item["startDate"], "%d/%m/%Y")
            if item["dueDate"]:
                item["dueDate"] = datetime.strptime(item["dueDate"], "%d/%m/%Y")
        self.data = data
        self.apply_and_validate()

    def apply_and_validate(self) -> None:
        assert self.data is not None
        if self.project is not None:
            for item in self.data:
                item["project"] = str(self.project["id"])
        self.results = None
        self.update_ingest_button()
        self.query_one("#editor", TextArea).clear()
        table = self.query_one("#table", WorkPackageTable)
        table.clear()
        for index, item in enumerate(self.data):
            table.add_row(*(table_cell(item[field]) for field in WorkPackage.model_fields), key=str(index))
        self.validate_data()

    @work(exclusive=True, group="validate")
    async def validate_data(self) -> None:
        assert self.data is not None
        table = self.query_one("#table", WorkPackageTable)
        table.loading = True
        results = await asyncio.to_thread(load_data, [dict(item) for item in self.data])
        table.loading = False
        self.results = results
        self.update_ingest_button()
        if results.validation_status:
            self.notify("Validation successful.", title="Success", severity="information")
            return

        self.notify("Validation failed. Click the red * for details.", title="Validation Error", severity="warning")
        for key, errors in results.validation_errors.items():
            for error in errors:
                if error["field"] in table.columns:
                    table.update_cell(row_key=str(key), column_key=error["field"], value=Text("*", style="red"))
                else:
                    self.notify(
                        f"Row {key + 1}, {error['field']}: {error['message']}",
                        title="Validation Error",
                        severity="error",
                        markup=False,
                    )

    @work(group="ingest")
    async def ingest_data(self, results: ValidationResponseList) -> None:
        table = self.query_one("#table", WorkPackageTable)
        table.loading = True
        created = 0
        for index, payload in results.validation_results.items():
            status, response = await asyncio.to_thread(create_workpackage, payload)
            if 200 <= status < 300:
                created += 1
            else:
                message = f"Row {index + 1}: {response['message']}"
                self.notify(message, title="Ingestion Error", severity="error", markup=False)
        table.loading = False
        self.lock_inputs(False)
        total = len(results.validation_results)
        self.notify(f"Created {created} of {total} work packages.", title="Ingestion", severity="information")

    def on_button_pressed(self) -> None:
        assert self.results is not None
        self.lock_inputs(True)
        self.ingest_data(self.results)
        self.results = None
        self.update_ingest_button()

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        row_key = event.cell_key.row_key.value
        assert row_key is not None
        if self.results:
            validation_errors: list[dict] = self.results.validation_errors[int(row_key)]
            column_key = event.cell_key.column_key.value
            text_editor = self.query_one("#editor", TextArea)
            for error in validation_errors:
                if error["field"] == column_key:
                    text_editor.text = f"{error['message']}"
                    break


def main() -> None:
    app = OpenProjectImporterApp()
    app.run()
    sys.exit(app.return_code or 0)


if __name__ == "__main__":
    main()
