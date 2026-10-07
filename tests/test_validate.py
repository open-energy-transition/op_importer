import pytest

from op_importer import main
from op_importer.data_model import ValidationResponse, WorkPackage
from op_importer.validate import KnownIds, ValidateWorkPackage, validate

KNOWN_IDS = KnownIds(projects=frozenset({4}), types=frozenset({3}))


@pytest.mark.parametrize(
    ("api_key", "expected_field"),
    [("type", "work_package_type"), ("subject", "subject"), ("priority", "priority")],
)
def test_validate_maps_api_error_fields(fake_api: dict[str, dict], api_key: str, expected_field: str) -> None:
    fake_api["/work_packages/form"]["_embedded"]["validationErrors"] = {api_key: {"message": "is invalid"}}
    payload = WorkPackage(subject="Test Work Package", project=4, work_package_type=3)

    assert validate(payload, KNOWN_IDS).validation_errors == [{"field": expected_field, "message": "is invalid"}]


@pytest.mark.parametrize("route", ["/projects", "/types"])
def test_validate_fails_fast_on_truncated_collection(fake_api: dict[str, dict], route: str) -> None:
    fake_api[route]["total"] += 1

    with pytest.raises(ValueError, match="Fetched only"):
        main([{"subject": "Test Work Package", "project": 4, "work_package_type": 3}])


@pytest.mark.live
class TestValidateWorkPackage:

    def test_validate_valid_payload(self):

        payload = WorkPackage(
            subject="Test Work Package",
            description="This is a test work package.",
            project=5,
            work_package_type=3,
            status=1,
        )

        actual = validate(payload, KnownIds.fetch())

        assert isinstance(actual, ValidationResponse), f"Expected a ValidationResponse, but got {type(actual)}"
        errors = actual.validation_errors
        assert len(errors) == 0, f"Expected no validation errors, but got {len(errors)}: {errors}"

    def test_get_form_work_package(self):

        payload = WorkPackage(
            subject="Test Work Package",
            description="This is a test work package.",
            project=5,
            work_package_type=3,
            status=1,
        )
        validator = ValidateWorkPackage(payload, KnownIds.fetch())
        status_code, response = validator.get_form()
        assert status_code == 200, f"Expected status code 200, but got {status_code}"
        assert isinstance(response, dict), f"Expected response to be a dict, but got {type(response)}"
