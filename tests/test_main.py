from collections import OrderedDict

from pytest import fixture

from op_importer import main


@fixture(scope="module")
def valid_input_file():
    data = [
        {
            "subject": "Test Work Package",
            "description": "This is a test work package",
            "project": 5,
            "work_package_type": 3,
            "status": 1,
            "startDate": None,
            "dueDate": None,
        },
        {
            "subject": "Test Work Package 2",
            "description": "This is another test work package",
            "project": 5,
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
    assert actual.validation_status is False

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
    assert actual.validation_errors == expected


def test_ingest_valid(valid_input_file):
    actual = main(valid_input_file)
    # assert actual["validation_status"] is True
    assert actual.validation_errors == OrderedDict({0: [], 1: []})
    assert actual.validation_results == {
        0: {
            "subject": "Test Work Package",
            "description": {
                "format": "markdown",
                "html": '<p class="op-uc-p">This is a test work package</p>',
                "raw": "This is a test work package",
            },
            "dueDate": None,
            "duration": None,
            "estimatedTime": None,
            "ignoreNonWorkingDays": False,
            "percentageDone": None,
            "scheduleManually": True,
            "startDate": None,
            "_links": {
                "assignee": {
                    "href": None,
                },
                "budget": {
                    "href": None,
                },
                "category": {
                    "href": None,
                },
                "parent": {
                    "href": None,
                    "title": None,
                },
                "priority": {
                    "href": "/api/v3/priorities/8",
                    "title": "Normal",
                },
                "project": {
                    "href": "/api/v3/projects/5",
                    "title": "Other Projects",
                },
                "projectPhase": {
                    "href": None,
                    "title": None,
                },
                "projectPhaseDefinition": {
                    "href": None,
                    "title": None,
                },
                "responsible": {
                    "href": None,
                },
                "status": {
                    "href": "/api/v3/statuses/1",
                    "title": "New",
                },
                "type": {
                    "href": "/api/v3/types/3",
                    "title": "Summary task",
                },
                "version": {
                    "href": None,
                },
            },
        },
        1: {
            "subject": "Test Work Package 2",
            "description": {
                "format": "markdown",
                "html": '<p class="op-uc-p">This is another test work package</p>',
                "raw": "This is another test work package",
            },
            "dueDate": None,
            "duration": None,
            "estimatedTime": None,
            "ignoreNonWorkingDays": False,
            "percentageDone": None,
            "scheduleManually": True,
            "startDate": None,
            "_links": {
                "assignee": {
                    "href": None,
                },
                "budget": {
                    "href": None,
                },
                "category": {
                    "href": None,
                },
                "parent": {
                    "href": None,
                    "title": None,
                },
                "priority": {
                    "href": "/api/v3/priorities/8",
                    "title": "Normal",
                },
                "project": {
                    "href": "/api/v3/projects/5",
                    "title": "Other Projects",
                },
                "projectPhase": {
                    "href": None,
                    "title": None,
                },
                "projectPhaseDefinition": {
                    "href": None,
                    "title": None,
                },
                "responsible": {
                    "href": None,
                },
                "status": {
                    "href": "/api/v3/statuses/1",
                    "title": "New",
                },
                "type": {
                    "href": "/api/v3/types/1",
                    "title": "Task",
                },
                "version": {
                    "href": None,
                },
            },
        },
    }
