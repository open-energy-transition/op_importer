from . import get_data
from . import validate

from logging import getLogger

logger = getLogger(__name__)


def main(input_file: list[dict]) -> dict:
    """Validate and Ingest a list of workpackages

    Parameters
    ----------
    input_file : list
        A list of dictionaries where the keys correspond to the fields
        required for defining a workpackage. Requires fields are ``subject``, 
        ``task`` and ``status``.
    
    Returns
    -------
    dict
        A dictionary containing keys ``validation errors``, and ``validation_status``. 
        If ``validation_status`` is True, then all the provided work packages in the
        ``input_file`` are validated by the API and the work packages are
        ingested.
    """

    result = {}
    validation_errors = []

    for item in input_file:
        validation_results = []
        validation_errors = validate.validate(item, asset='work_package')
        if validation_errors:
            logger.info(f"Validation errors for item '{item.get('subject', 'Unknown')}':")
            for error in validation_errors:
                logger.info(f" - Field: {error['field']}, Message: {error['message']}")
                validation_results.append(error)
            result.validation_status = False
        else:
            logger.info(f"Item '{item.get('subject', 'Unknown')}' is valid.")
            result.validation_status = True
        validation_errors.append(validation_results)

    return result
