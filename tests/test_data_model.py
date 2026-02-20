from op_importer.data_model import WorkPackage


def test_work_package_serialization():

    work_package = WorkPackage(
        subject="Test Work Package",
        description="This is a test work package",
        project=3,
        work_package_type=3,
        status=1,
    )

    expected_serialized = {
        "subject": "Test Work Package",
        "description": {"raw": "This is a test work package", "format": "markdown"},
        "project": {"href": "/api/v3/projects/3"},
        "type": {"href": "/api/v3/types/3"},
        "status": {"href": "/api/v3/statuses/1"},
    }

    actual_serialized = work_package.model_dump(by_alias=True)
    assert (
        actual_serialized == expected_serialized
    ), f"Expected {expected_serialized}, but got {actual_serialized}"
