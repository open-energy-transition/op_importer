from op_importer import main

from pytest import fixture

@fixture(scope="module")
def valid_input_file():
    data = [{'subject': 'Test Work Package', 'description': 'This is a test work package', 'project': 'Test', 'type': 'Task', 'status': 'New'},
            {'subject': 'Test Work Package 2', 'description': 'This is another test work package', 'project': 'Test', 'type': 'Milestone', 'status': 'Scheduled'}]
    return data

@fixture(scope="module")
def invalid_input_file():
    data = [{'subject': 'Test Work Package', 'description': 'This is a test work package', 'NOT_A_KEY': "", 'type': 'Task', 'status': 'INVALID'},
            {'subject': 'Test Work Package 2', 'description': 'This is another test work package', 'project': 'INVALID', 'type': 'Milestone'}]
    return data


def test_ingest_invalid(invalid_input_file):
    actual = main(invalid_input_file)
    assert actual.validation_status is False
    assert actual.validation_errors == [[{"field": 'status',
                                          "message": "Status 'INVALID' does not exist"}],
                                        [{"field": 'project',
                                          "message": "'INVALID' does not exist"}]]
    with ValueError as exc:
        assert str(exc.value) == "Validation failed for one or more items. See log for details."


def test_ingest_valid(valid_input_file):
    actual = main(valid_input_file)
    assert actual.validation_status is True
    assert actual.validation_errors == []
