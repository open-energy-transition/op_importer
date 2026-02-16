'''Use the OpenProject API for the localhost:8080 to obtain a list of users, roles, projects, and work packages.'''
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

def get_users():
    response = requests.get(f"{API_URL}/users", headers=HEADERS, auth=AUTH)
    return response.json()
def get_roles():
    response = requests.get(f"{API_URL}/roles", headers=HEADERS, auth=AUTH)
    return response.json()
def get_projects():
    response = requests.get(f"{API_URL}/projects", headers=HEADERS, auth=AUTH)
    return response.json()
def get_work_packages():
    response = requests.get(f"{API_URL}/work_packages", headers=HEADERS, auth=AUTH)
    return response.json()
def get_types():
    response = requests.get(f"{API_URL}/types", headers=HEADERS, auth=AUTH)
    return response.json()
def get_statuses():
    response = requests.get(f"{API_URL}/statuses", headers=HEADERS, auth=AUTH)
    return response.json()

def get_workpackage_form(workspace_id: int) -> tuple[int, dict]:
    url = f"{API_URL}/workspaces/{workspace_id}/work_packages/form"
    response = requests.post(url, headers=HEADERS, auth=AUTH)
    return response.status_code, response.json()

def prepare_workpackage(workspace_id: int, subject: str, description: str, type: int = 1, status: int = 1) -> tuple[int, dict]:
    """
    Creates a work package in the specified workspace
    
    Parameters
    ----------
    workspace_id: int
        ID of the workspace where the work package will be created
    subject: str
        Subject of the work package
    description: str
        Description of the work package
    type: int
        Type ID of the work package e.g. 1=Task, 2=Milestone, 3=Phase, 4=Deliverable
    status: int
        Status ID of the work package e.g. 1=New, 2=In Progress, 3=Resolved, 4=Feedback, 5=Closed, 6=Rejected
    """
    url = f"{API_URL}/workspaces/{workspace_id}/work_packages/form"
    payload = {
        "subject": subject,
        "description": {
            "raw": description,
            "format": "markdown"
        }
        ,
        "startDate": str(datetime.now().date().isoformat()),
        "duration": "P1D",
        "ignoreNonWorkingDays": True,
        "type": {
            "href": f"/api/v3/types/{type}"
        },
        "status": {
            "href": f"/api/v3/statuses/{status}"
        }}
    response = requests.post(url, headers=HEADERS, auth=AUTH, json=payload)
    return response.status_code, response.json()


def create_workpackage(payload: dict) -> tuple[int, dict]:
    url = f"{API_URL}/work_packages"
    response = requests.post(url, headers=HEADERS, auth=AUTH, json=payload)
    return response.status_code, response.json()


if __name__ == "__main__": 

    status, response = get_workpackage_form(workspace_id=6)
    print("Status:", status)
    if status == 200:
        payload = response['_embedded']['payload']
        if response['_embedded']['validationErrors']:
            for field, error in response['_embedded']['validationErrors'].items():
                print(f"Validation error for '{field}': {error['message']}")
            response['_embedded']['payload']['subject'] = "Test Work Package"
            status, response = create_workpackage(payload)
            print("Status:", status)
            if status == 200:
                print("")
