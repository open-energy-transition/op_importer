from collections import OrderedDict
from logging import basicConfig, getLogger
from typing import Any

from pydantic import ValidationError
from textual.logging import TextualHandler

from . import validate
from .data_model import ValidationResponseList, WorkPackage

basicConfig(level="NOTSET", handlers=[TextualHandler()])

logger = getLogger(__name__)


def extract_validation_errors(validation_errors: list) -> list[dict[str, str]]:
    """Extract validation errors from the results returned by the API.

    Parameters
    ----------
    validation_results : list
        A list of validation results returned by the API. Each item in the list is a dictionary
        containing a 'field' key and a 'message' key.

    Returns
    -------
    list
        A list of dictionaries, where each dictionary contains a 'field' key and a 'message' key,
        representing the validation errors extracted from the API response.
    """
    errors = []
    for error in validation_errors:
        logger.info(f" - Field: {error['field']}, Message: {error['message']}")
        errors.append(error)
    return errors


def main(input_file: list[dict]) -> ValidationResponseList:
    """Validate and Ingest a list of work packages

    Parameters
    ----------
    input_file : list
        A list of dictionaries where the keys correspond to the fields
        required for defining a work package. Required fields are ``subject``,
        ``task`` and ``status``.

    Returns
    -------
    dict
        A dictionary containing keys ``validation errors``, and ``validation_status``.
        If ``validation_status`` is True, then all the provided work packages in the
        ``input_file`` are validated by the API and the work packages are
        ingested.
    """
    result = ValidationResponseList(
        validation_status=True, validation_errors=OrderedDict(), validation_results=OrderedDict()
    )

    validation_results: dict[int, Any] = {}
    validation_errors = {}

    for index, item in enumerate(input_file):
        error_list = []
        # Use Pydantic model to validate the input data structure and types
        # before sending to API
        try:
            payload = WorkPackage(**item)
        except ValidationError as exc:
            for error in exc.errors():
                error_list.append({"field": error["loc"][0], "message": error["msg"]})
                logger.info(f"Validation error for item {error['loc'][0]} - {error['msg']}")
            result.validation_status = False
        else:
            response = validate.validate(payload)  # typing: ValidationResponse
            if response.validation_status is False:
                errors = response.validation_errors
                error_list.extend(extract_validation_errors(errors))
                result.validation_status = False
            else:
                logger.info(f"Item '{item.get('subject', 'Unknown')}' is valid.")
                validation_results[index] = response.validation_results

        validation_errors[index] = error_list

    result.validation_results = validation_results
    result.validation_errors = validation_errors

    return result
