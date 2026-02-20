from datetime import datetime

from op_importer.data_model import WorkPackage


def test_work_package_serialization():

    work_package = WorkPackage(
        subject="Test Work Package",
        description="This is a test work package",
        project=3,
        work_package_type=3,
        status=1,
        startDate=datetime(1982, 6, 13),
        dueDate=datetime(2024, 6, 30),
    )

    expected_serialized = {
        "subject": "Test Work Package",
        "description": {"raw": "This is a test work package", 
                        "format": "markdown"},
        "project": {"href": "/api/v3/projects/3"},
        "type": {"href": "/api/v3/types/3"},
        "status": {"href": "/api/v3/statuses/1"},
        "startDate": "1982-06-13",
        "dueDate": "2024-06-30",
    }

    actual_serialized = work_package.model_dump(by_alias=True)
    assert (
        actual_serialized == expected_serialized
    ), f"Expected {expected_serialized}, but got {actual_serialized}"


def test_work_package_serialization_defaults():

    work_package = WorkPackage(subject="Test Work Package", 
                               work_package_type=3)

    expected_serialized = {
        "subject": "Test Work Package",
        "description": {},
        "project": {},
        "type": {"href": "/api/v3/types/3"},
        "status": {},
        "startDate": None,
        "dueDate": None,
    }

    actual_serialized = work_package.model_dump(by_alias=True)
    assert (
        actual_serialized == expected_serialized
    ), f"Expected {expected_serialized}, but got {actual_serialized}"
