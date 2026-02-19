from collections import OrderedDict

from pytest import fixture

from op_importer import main


@fixture(scope="module")
def valid_input_file():
    data = [
        {
            "subject": "Test Work Package",
            "description": "This is a test work package",
            "project": 3,
            "work_package_type": 3,
            "status": 1,
        },
        {
            "subject": "Test Work Package 2",
            "description": "This is another test work package",
            "project": 4,
            "work_package_type": 1,
            "status": 2,
        },
    ]
    return data


@fixture(scope="module")
def invalid_input_file():
    data = [
        {
            "subject": "Test Work Package",
            "description": "This is a test work package",
            "NOT_A_KEY": "",
            "type": "Task",
            "status": "INVALID",
        },
        {
            "subject": "Test Work Package 2",
            "description": "This is another test work package",
            "project": "INVALID",
            "type": "Milestone",
        },
    ]
    return data


def test_ingest_invalid(invalid_input_file):
    actual = main(invalid_input_file)
    assert actual["validation_status"] is False

    expected = OrderedDict(
        {
            0: [
                {"field": "work_package_type", "message": "Field required"},
                {
                    "field": "status",
                    "message": "Input should be a valid integer, unable to parse string as an integer",
                },
            ],
            1: [
                {
                    "field": "project",
                    "message": "Input should be a valid integer, unable to parse string as an integer",
                },
                {"field": "work_package_type", "message": "Field required"},
            ],
        }
    )
    assert actual["validation_errors"] == expected


def test_ingest_valid(valid_input_file):
    actual = main(valid_input_file)
    assert actual["validation_status"] is True
    assert actual["validation_errors"] == OrderedDict({0: [], 1: []})
