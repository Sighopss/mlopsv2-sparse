"""Tests validating workflow YAML structure for GitHub Actions MLOps CI/CD.

Validates:
- All workflows contain workflow_dispatch trigger (Property 6) — Requirements 3.7, 4.6, 5.5, 6.5
- All workflows use azure/login with OIDC from secrets (Property 4) — Requirements 2.1, 2.2, 7.1
- No workflow contains hardcoded credentials (Property 5) — Requirements 2.4, 7.3
- Infra workflow contains terraform init/plan/apply steps — Requirements 3.1
- Training workflow contains az ml data/environment/compute/job create steps — Requirements 4.6
- Online deployment workflow contains endpoint/deployment/traffic steps — Requirements 5.5
- Batch deployment workflow contains compute/endpoint/deployment steps — Requirements 6.5
"""

import os
import re

import pytest
import yaml

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
WORKFLOWS_DIR = os.path.join(REPO_ROOT, ".github", "workflows")

WORKFLOW_FILES = [
    "tf-gha-deploy-infra.yml",
    "deploy-model-training-pipeline-classical.yml",
    "deploy-online-endpoint-pipeline-classical.yml",
    "deploy-batch-endpoint-pipeline-classical.yml",
]


def load_workflow(filename):
    """Load and parse a workflow YAML file."""
    path = os.path.join(WORKFLOWS_DIR, filename)
    with open(path, "r") as f:
        return yaml.safe_load(f)


def read_workflow_raw(filename):
    """Read raw text content of a workflow file."""
    path = os.path.join(WORKFLOWS_DIR, filename)
    with open(path, "r") as f:
        return f.read()


# --- Property 6: All workflows support manual triggering ---


@pytest.mark.parametrize("workflow_file", WORKFLOW_FILES)
def test_workflow_dispatch_trigger(workflow_file):
    """Every workflow must include workflow_dispatch in its triggers.

    Validates: Requirements 3.7, 4.6, 5.5, 6.5
    """
    workflow = load_workflow(workflow_file)
    triggers = workflow.get("on", workflow.get(True, {}))
    if isinstance(triggers, dict):
        assert "workflow_dispatch" in triggers, (
            f"{workflow_file}: missing workflow_dispatch trigger"
        )
    elif isinstance(triggers, list):
        assert "workflow_dispatch" in triggers, (
            f"{workflow_file}: missing workflow_dispatch trigger"
        )
    else:
        pytest.fail(f"{workflow_file}: unexpected 'on' trigger format: {triggers}")


# --- Property 4: All workflows use OIDC authentication from secrets ---


OIDC_PARAMS = ["client-id", "tenant-id", "subscription-id"]


@pytest.mark.parametrize("workflow_file", WORKFLOW_FILES)
def test_oidc_auth_with_secrets(workflow_file):
    """Every workflow must have at least one job with azure/login@v2 using OIDC
    parameters sourced from secrets.

    Validates: Requirements 2.1, 2.2, 7.1
    """
    workflow = load_workflow(workflow_file)
    jobs = workflow.get("jobs", {})

    found_oidc = False
    for job_name, job_def in jobs.items():
        steps = job_def.get("steps", [])
        for step in steps:
            uses = step.get("uses", "")
            if "azure/login" in uses:
                with_params = step.get("with", {})
                for param in OIDC_PARAMS:
                    assert param in with_params, (
                        f"{workflow_file} job '{job_name}': azure/login missing '{param}'"
                    )
                    value = str(with_params[param])
                    assert "secrets." in value, (
                        f"{workflow_file} job '{job_name}': '{param}' must reference secrets.*, got: {value}"
                    )
                found_oidc = True

    assert found_oidc, (
        f"{workflow_file}: no job found with azure/login OIDC step"
    )


# --- Property 5: No hardcoded credentials ---

# GUID pattern: 8-4-4-4-12 hex digits (common format for Azure IDs)
GUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


@pytest.mark.parametrize("workflow_file", WORKFLOW_FILES)
def test_no_hardcoded_credentials(workflow_file):
    """No workflow should contain hardcoded GUIDs in credential positions
    or AZURE_CREDENTIALS references.

    Validates: Requirements 2.4, 7.3
    """
    raw = read_workflow_raw(workflow_file)

    # Check no AZURE_CREDENTIALS reference (old-style service principal JSON)
    assert "AZURE_CREDENTIALS" not in raw, (
        f"{workflow_file}: contains AZURE_CREDENTIALS reference"
    )

    # Check for hardcoded GUIDs in credential-related lines
    credential_keys = ["client-id", "tenant-id", "subscription-id", "client_secret"]
    for line in raw.splitlines():
        stripped = line.strip()
        for key in credential_keys:
            if key in stripped:
                guids = GUID_PATTERN.findall(stripped)
                assert len(guids) == 0, (
                    f"{workflow_file}: hardcoded GUID found in credential line: {stripped}"
                )


# --- Infra workflow: terraform init/plan/apply steps ---


def test_infra_workflow_terraform_steps():
    """Infra workflow must contain terraform init, plan, and apply steps.

    Validates: Requirements 3.1
    """
    raw = read_workflow_raw("tf-gha-deploy-infra.yml")
    assert "terraform init" in raw, "Infra workflow missing 'terraform init'"
    assert "terraform plan" in raw, "Infra workflow missing 'terraform plan'"
    assert "terraform apply" in raw, "Infra workflow missing 'terraform apply'"


# --- Training workflow: az ml data/environment/compute/job create steps ---


def test_training_workflow_ml_steps():
    """Training workflow must contain az ml data, environment, compute, and job
    create steps.

    Validates: Requirements 4.6
    """
    raw = read_workflow_raw("deploy-model-training-pipeline-classical.yml")
    assert "az ml data create" in raw, "Training workflow missing 'az ml data create'"
    assert "az ml environment create" in raw, (
        "Training workflow missing 'az ml environment create'"
    )
    assert "az ml compute create" in raw, (
        "Training workflow missing 'az ml compute create'"
    )
    assert "az ml job create" in raw, "Training workflow missing 'az ml job create'"


# --- Online deployment workflow: endpoint/deployment/traffic steps ---


def test_online_deployment_workflow_steps():
    """Online deployment workflow must contain endpoint create, deployment create,
    and traffic allocation steps.

    Validates: Requirements 5.5
    """
    raw = read_workflow_raw("deploy-online-endpoint-pipeline-classical.yml")
    assert "az ml online-endpoint create" in raw, (
        "Online workflow missing 'az ml online-endpoint create'"
    )
    assert "az ml online-deployment create" in raw, (
        "Online workflow missing 'az ml online-deployment create'"
    )
    assert "az ml online-endpoint update" in raw, (
        "Online workflow missing 'az ml online-endpoint update' (traffic allocation)"
    )


# --- Batch deployment workflow: compute/endpoint/deployment steps ---


def test_batch_deployment_workflow_steps():
    """Batch deployment workflow must contain compute create, batch-endpoint create,
    and batch-deployment create steps.

    Validates: Requirements 6.5
    """
    raw = read_workflow_raw("deploy-batch-endpoint-pipeline-classical.yml")
    assert "az ml compute create" in raw, (
        "Batch workflow missing 'az ml compute create'"
    )
    assert "az ml batch-endpoint create" in raw, (
        "Batch workflow missing 'az ml batch-endpoint create'"
    )
    assert "az ml batch-deployment create" in raw, (
        "Batch workflow missing 'az ml batch-deployment create'"
    )
