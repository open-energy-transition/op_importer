import sys
from csv import QUOTE_NOTNULL, DictReader
from datetime import datetime
from pathlib import Path
from typing import Iterable

from rich.text import Text
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
from op_importer.data_model import ValidationResponseList
from op_importer.get_data import (
    create_workpackage,
    get_projects,
    get_roles,
    get_statuses,
    get_types,
    get_users,
    get_work_packages,
)


class FilteredDirectoryTree(DirectoryTree):
    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        for path in paths:
            if path.is_file() and path.name.endswith(".csv"):
                yield path
            elif path.is_dir():
                yield path


class WorkPackageTable(DataTable):

    def on_mount(self) -> None:
        self.add_columns(
            ("Subject", "subject"),
            ("Description", "description"),
            ("Project", "project"),
            ("Type", "work_package_type"),
            ("Status", "status"),
            ("Start Date", "startDate"),
            ("Due Date", "dueDate"),
        )


class OpenProjectImporterApp(App[int]):
    """A Textual app for importing data into OpenProject."""

    TITLE = "OpenProject Importer"
    SUB_TITLE = "Validate and Ingest data into OpenProject"

    def get_data(self):
        self.users = get_users()
        self.roles = get_roles()
        self.projects = get_projects()
        self.work_packages = get_work_packages()
        self.types = get_types()
        self.statuses = get_statuses()

    def get_project_names(self):
        return [project["name"] for project in self.projects["_embedded"]["elements"]]

    def compose(self) -> ComposeResult:
        self.data = None
        self.results: ValidationResponseList | None = None
        self.get_data()
        yield Header()
        yield Label("Select a CSV file to import:")
        yield Horizontal(
            Vertical(
                FilteredDirectoryTree("./"),
                Button("Load Selected File", variant="primary", id="load_button", disabled=True),
            ),
            Vertical(
                WorkPackageTable(id="table"), Button("Validate", id="validate_button", variant="success", disabled=True)
            ),
        )
        yield Rule()
        project_items = [ListItem(Label(f"{name}")) for name in self.get_project_names()]
        yield Label("Select a project to import into:")
        yield Horizontal(
            ListView(*project_items),
            Vertical(
                TextArea("", read_only=True, id="editor"),
                Button("Ingest", id="ingest_button", variant="success", disabled=True),
            ),
        )

        yield Footer()

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        self.file = None
        if event.path.is_file() and event.path.name.endswith(".csv"):
            self.file = event.path
            self.query_one("#load_button", Button).disabled = False
        else:
            self.query_one("#load_button", Button).disabled = True
        return

    def load_selected_file(self) -> None:
        # Clear loaded data and results before loading new file
        self.data = None
        self.results = None
        # Clear the table before loading new data
        table = self.query_one("#table", WorkPackageTable)
        table.clear()
        text_editor = self.query_one("#editor", TextArea)
        text_editor.clear()

        expected_headers = {"subject", "description", "project", "work_package_type", "status", "startDate", "dueDate"}
        # Load the selected file and validate the data
        with open(self.file, "r") as f:
            reader = DictReader(f, quoting=QUOTE_NOTNULL)
            fieldnames: list[str] = reader.fieldnames
            if set(fieldnames).intersection(expected_headers) != expected_headers:
                self.notify(
                    "Invalid CSV format. Please ensure the file has the correct headers.",
                    title="CSV Format Error",
                    severity="error",
                )
                print(reader.fieldnames)
                return

            data = list(reader)
        # Convert date strings to datetime objects
        for item in data:
            if item["startDate"]:
                item["startDate"] = datetime.strptime(item["startDate"], "%d/%m/%Y") if item["startDate"] else None
            if item["dueDate"]:
                item["dueDate"] = datetime.strptime(item["dueDate"], "%d/%m/%Y") if item["dueDate"] else None
        # Store the loaded data in the app state for validation and ingestion
        self.data = data

        # Load the data render the results in the table
        for index, item in enumerate(data):
            table.add_row(
                item["subject"],
                item["description"],
                item["project"],
                item["work_package_type"],
                item["status"],
                item["startDate"].date().isoformat() if item["startDate"] else None,  # typing = datetime
                item["dueDate"].date().isoformat() if item["dueDate"] else None,  # typing = datetime
                key=str(index),
            )

    def validate_data(self) -> None:
        if not self.data:
            self.notify(
                "No data loaded. Please load a CSV file before validating.", title="No Data", severity="warning"
            )
            return
        self.results = load_data(self.data)
        # Display the results in the text editor
        if self.results.validation_status is False:
            self.notify("Validation failed. Click the red * for details.", title="Validation Error", severity="warning")

            # Update the table to show which rows have validation errors
            table: WorkPackageTable = self.query_one("#table", WorkPackageTable)
            for key, errors in self.results.validation_errors.items():
                for error in errors:
                    table.update_cell(row_key=str(key), column_key=error["field"], value=Text("*", style="red"))
        else:
            self.notify("Validation successful.", title="Success", severity="information")

    def ingest_data(self) -> None:
        """Ingest the validated data into OpenProject."""
        if self.results:
            for key, validated_item in self.results.validation_results.items():
                status, response = create_workpackage(validated_item)
                if status >= 200 and status < 300:
                    self.notify(
                        f"Work package '{validated_item['subject']}' ingested successfully.",
                        title="Ingestion Success",
                        severity="success",
                    )
                else:
                    self.notify(
                        f"Failed to ingest work package '{validated_item}'.", title="Ingestion Error", severity="error"
                    )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "load_button":
            self.load_selected_file()
            if self.data:
                self.query_one("#validate_button", Button).disabled = False
            else:
                self.query_one("#validate_button", Button).disabled = True
                self.query_one("#ingest_button", Button).disabled = True
        elif button_id == "validate_button":
            self.validate_data()
            if self.results:
                if self.results.validation_status is True:
                    self.query_one("#ingest_button", Button).disabled = False
                else:
                    self.query_one("#ingest_button", Button).disabled = True
        elif button_id == "ingest_button":
            self.ingest_data()

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        row_key = int(event.cell_key.row_key.value)
        if self.results:
            validation_errors: list[dict] = self.results.validation_errors[row_key]
            column_key = event.cell_key.column_key.value
            text_editor = self.query_one("#editor", TextArea)
            for error in validation_errors:
                if error["field"] == column_key:
                    text_editor.text = f"{error['message']}"
                    break


def main():
    app = OpenProjectImporterApp()
    app.run()
    sys.exit(app.return_code or 0)


if __name__ == "__main__":
    main()
