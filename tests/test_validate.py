from op_importer.data_model import WorkPackage
from op_importer.validate import ValidateWorkPackage, validate


class TestValidateWorkPackage:

    def test_validate_valid_payload(self):

        payload = WorkPackage(
            subject="Test Work Package",
            description="This is a test work package.",
            project=3,
            work_package_type=3,
            status=1,
        )

        actual = validate(payload)

        assert isinstance(
            actual, list
        ), f"Expected a list of validation errors, but got {type(actual)}"
        assert (
            len(actual) == 0
        ), f"Expected no validation errors, but got {len(actual)}: {actual}"

    def test_get_form_work_package(self):

        payload = {
            "subject": "Test Work Package",
            "description": "This is a test work package.",
            "project": {"href": "/api/v3/projects/3"},
            "type": {"href": "/api/v3/types/3"},
            "status": {"href": "/api/v3/statuses/1"},
        }
        validator = ValidateWorkPackage(payload)
        status_code, response = validator.get_form(payload)
        assert status_code == 200, f"Expected status code 200, but got {status_code}"
        assert isinstance(
            response, dict
        ), f"Expected response to be a dict, but got {type(response)}"
