from op_importer.get_data import create_workpackage, get_users


def test_connection():
    users = get_users()
    assert isinstance(users, dict), f"Expected a dict of users, but got {type(users)}"
    assert len(users) > 0, "Expected at least one user, but got none"


def test_create_workpackage():

    payload = {
        "subject": "Test Work Package",
        "project": {"href": "/api/v3/projects/3"},
    }
    status, response = create_workpackage(payload=payload)
    assert status == 201, f"Expected status code 201, but got {status}"
    assert "id" in response, "Response does not contain 'id'"
    assert (
        response["subject"] == "Test Work Package"
    ), f"Expected subject 'Test Work Package', but got {response['subject']}"
