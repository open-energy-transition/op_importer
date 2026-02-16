from op_importer.validate import validate


def test_validate_empty_payload():

    payload = {}

    status = validate(payload, asset='work_package')

    assert isinstance(status, list), \
        f"Expected a list of validation errors, but got {type(status)}"
    assert len(status) > 0, \
        "Expected at least one validation error, but got none"
    for error in status:
        assert "field" in error and "message" in error, \
            f"Each validation error should contain 'field' and 'message', \
                but got {error}"


def test_validate_valid_payload():

    payload = {
        "subject": "Test Work Package",
        "project": {
            "href": "/api/v3/projects/1"
        },
        "type": {
            "href": "/api/v3/types/1"
        },
    }

    actual = validate(payload, asset='work_package')

    assert isinstance(actual, list), \
        f"Expected a list of validation errors, but got {type(actual)}"
    assert len(actual) == 0, \
        f"Expected no validation errors, but got {len(actual)}: {actual}"
