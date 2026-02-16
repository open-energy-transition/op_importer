from op_importer.get_data import create_workpackage


def test_create_workpackage():

    payload = {
        "subject": "Test Work Package",
        "project": {
            "href": "/api/v3/projects/6"
        }
    }   
    status, response = create_workpackage(payload=payload)
    assert status == 200, f"Expected status code 200, but got {status}"
    assert "id" in response, "Response does not contain 'id'"
    assert response["subject"] == "Test Work Package", f"Expected subject 'Test Work Package', but got {response['subject']}"
