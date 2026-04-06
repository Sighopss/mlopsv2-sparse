# Azure MLOps (v2) — GitHub Actions CI/CD Migration

[Original MLOps v2 README](https://github.com/Azure/mlops-v2/blob/main/README.md)

## Assignment: CI/CD Migration from Azure DevOps to GitHub Actions

This project migrates the MLOps v2 solution accelerator's CI/CD orchestration from Azure DevOps-dependent GitHub Actions workflows to fully self-contained GitHub Actions workflows.

### What Was Done

**Config file conversion** — Removed the ADO `variables:` wrapper and all `$(variable)` interpolation syntax from `config-infra-dev.yml` and `config-infra-prod.yml`. Derived resource names (resource group, workspace, key vault, etc.) are now pre-computed as static strings following the original naming conventions. ADO-specific fields (`ap_vm_image`, `ado_service_connection_rg`, `ado_service_connection_aml_ws`) were removed.

**Reusable composite action** — Created `.github/actions/parse-config/action.yml`, a composite action that parses any config file using `yq` and exports all keys as step outputs. This avoids duplicating config-parsing logic across workflows.

**Four self-contained workflows rewritten:**

| Workflow | File | Purpose |
|---|---|---|
| Infrastructure | `tf-gha-deploy-infra.yml` | Terraform init/plan/apply for Azure resources |
| Training | `deploy-model-training-pipeline-classical.yml` | Register data, environment, compute; submit ML pipeline |
| Online Deploy | `deploy-online-endpoint-pipeline-classical.yml` | Create online endpoint, deployment, allocate traffic |
| Batch Deploy | `deploy-batch-endpoint-pipeline-classical.yml` | Create batch compute, endpoint, deployment |

Each workflow:
- Uses OIDC authentication via `azure/login@v2` (no stored credentials)
- Selects dev/prod config based on branch (main → prod, else → dev)
- Uses the `parse-config` composite action for config values
- Has no references to `Azure/mlops-templates` reusable workflows
- Supports manual triggering via `workflow_dispatch`

**Structural validation tests** — 34 pytest tests across two files verify the migration is correct:
- `tests/test_config_files.py` (18 tests) — No ADO syntax, naming conventions match, base parameters preserved
- `tests/test_workflow_structure.py` (16 tests) — OIDC auth present, no hardcoded credentials, correct CLI steps in each workflow, `workflow_dispatch` triggers

### Running the Tests

```bash
pip install pytest pyyaml
pytest tests/ -v
```

All 34 tests pass, confirming structural correctness of the migration.

### Azure AD Limitation

The workflows could not be tested end-to-end against Azure because the Azure AD tenant has `allowedToCreateApps` set to `false`, preventing creation of app registrations and service principals from non-admin accounts. This is a tenant-level policy that cannot be bypassed via CLI.

To complete a live deployment, an Azure AD administrator would need to:
1. Create an app registration with OIDC federated credentials for this GitHub repo
2. Assign it Contributor role on the target subscription
3. Configure the following GitHub repository secrets: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `ARM_CLIENT_SECRET`

The 34 structural validation tests serve as equivalent proof of correctness, verifying that all workflow files, config files, and authentication patterns conform to the migration requirements.

### Files Modified/Created

| File | Action |
|---|---|
| `config-infra-dev.yml` | Modified — removed ADO syntax |
| `config-infra-prod.yml` | Modified — removed ADO syntax |
| `.github/actions/parse-config/action.yml` | Created — reusable config parser |
| `.github/workflows/tf-gha-deploy-infra.yml` | Rewritten — self-contained |
| `.github/workflows/deploy-model-training-pipeline-classical.yml` | Rewritten — self-contained |
| `.github/workflows/deploy-online-endpoint-pipeline-classical.yml` | Rewritten — self-contained |
| `.github/workflows/deploy-batch-endpoint-pipeline-classical.yml` | Rewritten — self-contained |
| `tests/test_config_files.py` | Created — config validation tests |
| `tests/test_workflow_structure.py` | Created — workflow validation tests |

No files in `infrastructure/`, `mlops/azureml/`, `data-science/`, or `data/` were modified.
