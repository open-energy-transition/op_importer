"""Validate the provided data for creating a work package in OpenProject.

This module contains functions to validate the data required for creating a 
work package in OpenProject. 
It checks for the presence of required fields, correct data types, 
and valid values according to the OpenProject API specifications.
"""

import requests
import json
from requests.auth import HTTPBasicAuth

from os import getenv
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

API_URL = "https://oet.openproject.com/api/v3"
API_KEY = getenv("OPENPROJECT_API_KEY", "")

HEADERS = {"Content-Type": "application/json"}
AUTH = HTTPBasicAuth('apikey', API_KEY)


class Validate:
    """Base class for validating data for OpenProject API requests."""

    def __init__(self, payload: dict):
        self.payload = payload
        self.errors = []
        self.validated_response = {}

    def validate(self) -> bool:

        status, response = self.get_form(self.payload)
        print("Status:", status)
        if status == 200:
            if (errors := response['_embedded']['validationErrors']):
                for field, error in errors.items():
                    self.errors.append({"field": field,
                                        "message": error['message']})
                return False
            else:
                self.validated_response = response['_embedded']['payload']
                return True
        else:
            error_message = response.get('message', 'Unknown error')
            raise ValueError(f"Failed to fetch form: {error_message}")

    def errors(self) -> list[dict[str, str]]:
        return self.errors


class ValidateWorkPackage(Validate):

    def get_form(self, payload: dict) -> tuple[int, dict]:
        url = f"{API_URL}/work_packages/form"
        response = requests.post(url, headers=HEADERS, auth=AUTH, json=payload)
        return response.status_code, response.json()


def validate(payload: dict, asset: str = 'work_package') -> list:

    if asset == 'work_package':
        validator = ValidateWorkPackage(payload)
    else:
        raise NotImplementedError(f"Validation for asset type '{asset}' is not implemented.")

    status = validator.validate()
    if status is True:
        return []
    else:
        return validator.errors
