# Implementation Plan: GitHub Actions MLOps CI/CD Migration

## Overview

Migrate CI/CD orchestration from ADO-dependent GitHub Actions workflows to self-contained GitHub Actions workflows. The implementation converts config files, creates a reusable composite action for config parsing, rewrites all four workflows (infra, training, online deploy, batch deploy) to use OIDC auth and direct `az ml` CLI commands, and adds structural validation tests.

## Tasks

- [x] 1. Convert environment config files to GitHub Actions format
  - [x] 1.1 Rewrite `config-infra-dev.yml` to remove the `variables:` wrapper and all `$(variable)` interpolation syntax, replacing derived names with pre-computed static strings (e.g., `resource_group: rg-mlopsv2-0001dev`)
    - Remove ADO service connection fields (`ado_service_connection_rg`, `ado_service_connection_aml_ws`)
    - Remove `ap_vm_image` field (GitHub runners are specified in workflow YAML)
    - Keep all base parameters (namespace, postfix, location, environment) and Terraform backend settings unchanged
    - _Requirements: 1.1, 1.2, 1.4_
  - [x] 1.2 Rewrite `config-infra-prod.yml` with the same changes as 1.1 but for prod environment values
    - _Requirements: 1.1, 1.2, 1.4_

- [x] 2. Create reusable composite action for config parsing
  - [x] 2.1 Create `.github/actions/parse-config/action.yml` composite action that accepts a config file path as input, parses it with `yq`, and exports all keys as step outputs
    - Validate the config file exists before parsing
    - Export each top-level key as a named output
    - _Requirements: 1.1, 1.2_

- [x] 3. Rewrite infrastructure provisioning workflow
  - [x] 3.1 Rewrite `.github/workflows/tf-gha-deploy-infra.yml` as a self-contained workflow
    - Add `push` and `workflow_dispatch` triggers
    - Add branch-detection job that selects `config-infra-dev.yml` for non-main branches and `config-infra-prod.yml` for main
    - Use the `parse-config` composite action to load config values
    - Add `azure/login@v2` step with OIDC (client-id, tenant-id, subscription-id from secrets)
    - Add `hashicorp/setup-terraform` step using `terraform_version` from config
    - Add `terraform init` step with `-backend-config` flags for storage account, resource group, container, key
    - Add `terraform plan` and `terraform apply` steps passing all required variables (location, prefix=namespace, environment, postfix, enable_aml_computecluster, enable_monitoring, client_secret) via `TF_VAR_` env vars
    - Remove all references to `Azure/mlops-templates` reusable workflows
    - _Requirements: 2.1, 2.2, 2.4, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 7.1, 7.2_

- [x] 4. Checkpoint - Validate infrastructure workflow
  - Ensure the infra workflow YAML is valid, review config files are correct, ask the user if questions arise.

- [x] 5. Rewrite ML training pipeline workflow
  - [x] 5.1 Rewrite `.github/workflows/deploy-model-training-pipeline-classical.yml` as a self-contained workflow
    - Add `push` and `workflow_dispatch` triggers
    - Add branch-detection and config-parsing jobs (same pattern as infra workflow)
    - Add `azure/login@v2` step with OIDC
    - Add step: `az ml data create --file mlops/azureml/train/data.yml --resource-group <from config> --workspace-name <from config>`
    - Add step: `az ml environment create --file mlops/azureml/train/train-env.yml --resource-group <from config> --workspace-name <from config>`
    - Add step: `az ml compute create --name cpu-cluster --type amlcompute --size Standard_DS3_v2 --min-instances 0 --max-instances 4 --tier low_priority` (with `|| true` to handle already-exists)
    - Add step: `az ml job create --file mlops/azureml/train/pipeline.yml --resource-group <from config> --workspace-name <from config>`
    - Remove all references to `Azure/mlops-templates` reusable workflows
    - _Requirements: 2.1, 2.2, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 7.1_

- [x] 6. Rewrite online endpoint deployment workflow
  - [x] 6.1 Rewrite `.github/workflows/deploy-online-endpoint-pipeline-classical.yml` as a self-contained workflow
    - Add `push` and `workflow_dispatch` triggers
    - Add branch-detection and config-parsing jobs
    - Add `azure/login@v2` step with OIDC
    - Add step: `az ml online-endpoint create --file mlops/azureml/deploy/online/online-endpoint.yml --name <endpoint-name> --resource-group <from config> --workspace-name <from config>` (with `|| true` for idempotency)
    - Add step: `az ml online-deployment create --file mlops/azureml/deploy/online/online-deployment.yml --endpoint-name <endpoint-name> --resource-group <from config> --workspace-name <from config> --all-traffic`
    - Add step: `az ml online-endpoint update --name <endpoint-name> --traffic "blue=100" --resource-group <from config> --workspace-name <from config>`
    - Remove all references to `Azure/mlops-templates` reusable workflows
    - _Requirements: 2.1, 2.2, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 7.1_

- [x] 7. Rewrite batch endpoint deployment workflow
  - [x] 7.1 Rewrite `.github/workflows/deploy-batch-endpoint-pipeline-classical.yml` as a self-contained workflow
    - Add `push` and `workflow_dispatch` triggers
    - Add branch-detection and config-parsing jobs
    - Add `azure/login@v2` step with OIDC
    - Add step: `az ml compute create --name batch-cluster --type amlcompute --size STANDARD_DS3_V2 --min-instances 0 --max-instances 5 --tier low_priority` (with `|| true`)
    - Add step: `az ml batch-endpoint create --file mlops/azureml/deploy/batch/batch-endpoint.yml --name <endpoint-name> --resource-group <from config> --workspace-name <from config>`
    - Add step: `az ml batch-deployment create --file mlops/azureml/deploy/batch/batch-deployment.yml --endpoint-name <endpoint-name> --resource-group <from config> --workspace-name <from config>`
    - Remove all references to `Azure/mlops-templates` reusable workflows
    - _Requirements: 2.1, 2.2, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 7.1_

- [x] 8. Checkpoint - Validate all workflows
  - Ensure all four workflow YAML files are syntactically valid, all use OIDC auth, all reference config parsing, no references to Azure/mlops-templates remain. Ask the user if questions arise.

- [x] 9. Add structural validation tests
  - [x] 9.1 Create `tests/test_config_files.py` with pytest tests validating config file structure
    - Test that no values contain `$(` pattern (example tests for Property 1)
    - Test that derived resource names match naming convention for both dev and prod configs (example tests for Property 2)
    - Test that base parameter values are preserved (namespace=mlopsv2, postfix=0001, etc.)
    - _Requirements: 1.1, 1.2, 1.4_
  - [ ]* 9.2 Write property test for config file ADO syntax absence
    - **Property 1: No ADO interpolation syntax in config files**
    - **Validates: Requirements 1.1**
  - [ ]* 9.3 Write property test for derived resource name consistency
    - **Property 2: Derived resource names match naming convention**
    - **Validates: Requirements 1.2**
  - [x] 9.4 Create `tests/test_workflow_structure.py` with pytest tests validating workflow YAML structure
    - Test that all workflows contain `workflow_dispatch` trigger (example tests for Property 6)
    - Test that all workflows use `azure/login` with OIDC parameters from secrets (example tests for Property 4)
    - Test that no workflow contains hardcoded credentials (example tests for Property 5)
    - Test infra workflow contains terraform init/plan/apply steps
    - Test training workflow contains az ml data/environment/compute/job create steps
    - Test online deployment workflow contains endpoint/deployment/traffic steps
    - Test batch deployment workflow contains compute/endpoint/deployment steps
    - _Requirements: 2.1, 2.2, 2.4, 3.1, 3.7, 4.6, 5.5, 6.5, 7.1, 7.3_
  - [ ]* 9.5 Write property test for branch-based environment selection logic
    - **Property 3: Branch-based environment selection**
    - **Validates: Requirements 1.3, 3.4, 3.5, 4.7, 4.8, 5.6, 5.7, 6.6, 6.7**
  - [ ]* 9.6 Write property test for OIDC auth across all workflows
    - **Property 4: All workflows use OIDC authentication from secrets**
    - **Validates: Requirements 2.1, 2.2, 7.1**
  - [ ]* 9.7 Write property test for no hardcoded credentials
    - **Property 5: No hardcoded credentials in workflow or config files**
    - **Validates: Requirements 2.4, 7.3**
  - [ ]* 9.8 Write property test for workflow_dispatch presence
    - **Property 6: All workflows support manual triggering**
    - **Validates: Requirements 3.7, 4.6, 5.5, 6.5**
  - [ ]* 9.9 Write property test for config-derived az ml parameters
    - **Property 7: All az ml commands use config-derived resource group and workspace**
    - **Validates: Requirements 4.5, 5.4, 6.4**

- [x] 10. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using pytest + hypothesis
- Unit tests validate specific structural expectations of generated YAML files
- Existing files in `infrastructure/`, `mlops/azureml/`, `data-science/`, and `data/` are never modified (Requirement 8)
