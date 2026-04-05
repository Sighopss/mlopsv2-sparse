# Requirements Document

## Introduction

This document specifies the requirements for migrating the Azure MLOps v2 solution accelerator's CI/CD orchestration from Azure DevOps pipelines to GitHub Actions workflows. The migration covers infrastructure provisioning (Terraform), ML training pipeline submission, and model deployment (online and batch endpoints). Existing Azure ML pipeline YAML, Terraform code, and data-science source code remain unchanged — only CI/CD orchestration files are modified or created.

## Glossary

- **Workflow**: A GitHub Actions workflow defined as a YAML file in `.github/workflows/`
- **GitHub_Environment**: A GitHub deployment environment (e.g., `dev`, `prod`) with associated secrets and protection rules
- **OIDC_Credential**: An OpenID Connect federated identity credential configured on an Azure AD app registration, enabling passwordless authentication from GitHub Actions to Azure
- **Config_File**: An environment-specific configuration file (`config-infra-dev.yml` or `config-infra-prod.yml`) containing infrastructure and deployment parameters
- **Infra_Workflow**: The GitHub Actions workflow responsible for Terraform-based infrastructure provisioning
- **Training_Workflow**: The GitHub Actions workflow responsible for registering data assets, creating environments, and submitting the Azure ML training pipeline
- **Deployment_Workflow**: The GitHub Actions workflow(s) responsible for creating and configuring online and batch endpoints
- **AML_Workspace**: The Azure Machine Learning workspace provisioned by Terraform
- **Terraform_Backend**: The Azure Storage Account used for Terraform remote state, configured via `azurerm` backend

## Requirements

### Requirement 1: Environment Configuration Conversion

**User Story:** As a DevOps engineer, I want environment configuration files compatible with GitHub Actions, so that workflows can resolve infrastructure parameters without Azure DevOps variable template syntax.

#### Acceptance Criteria

1. WHEN the Infra_Workflow reads a Config_File, THE Workflow SHALL resolve all parameter values (namespace, postfix, location, environment, resource names, Terraform backend settings) as plain key-value pairs without ADO `$(variable)` interpolation syntax
2. WHEN a Config_File is loaded, THE Workflow SHALL compute derived resource names (resource_group, aml_workspace, key_vault, container_registry, storage_account) from the base parameters (namespace, postfix, environment) using the same naming conventions as the original ADO templates
3. WHEN switching between dev and prod environments, THE Workflow SHALL select the correct Config_File based on the Git branch (non-main branches use dev, main branch uses prod)
4. THE Config_File SHALL retain all original parameter values (namespace: mlopsv2, postfix: 0001, location: eastus) and Terraform backend settings (terraform_version, terraform_st_container_name, terraform_st_key) without modification

### Requirement 2: Azure Authentication via OIDC

**User Story:** As a DevOps engineer, I want GitHub Actions workflows to authenticate to Azure using OIDC federated credentials, so that no long-lived secrets are stored in the repository.

#### Acceptance Criteria

1. THE Workflow SHALL authenticate to Azure using the `azure/login` GitHub Action with OIDC federated credentials (client-id, tenant-id, subscription-id)
2. THE Workflow SHALL retrieve Azure authentication parameters (client-id, tenant-id, subscription-id) from GitHub repository secrets or GitHub_Environment secrets
3. WHEN OIDC authentication fails, THE Workflow SHALL fail the job with a clear error message and stop execution
4. THE Workflow SHALL NOT store or reference Azure client secrets for authentication in any workflow file

### Requirement 3: Infrastructure Provisioning Workflow

**User Story:** As a DevOps engineer, I want a GitHub Actions workflow that provisions Azure infrastructure via Terraform, so that infrastructure changes are applied through CI/CD.

#### Acceptance Criteria

1. WHEN the Infra_Workflow is triggered, THE Infra_Workflow SHALL execute Terraform init, plan, and apply steps against the `infrastructure/` directory
2. WHEN executing Terraform init, THE Infra_Workflow SHALL configure the azurerm backend using the Terraform_Backend parameters (storage account, resource group, container name, key) from the selected Config_File
3. WHEN executing Terraform plan and apply, THE Infra_Workflow SHALL pass all required Terraform variables (location, prefix, environment, postfix, enable_aml_computecluster, enable_monitoring, client_secret) from the Config_File and GitHub secrets
4. WHEN a push occurs to the main branch, THE Infra_Workflow SHALL provision infrastructure using the prod Config_File
5. WHEN a push occurs to a non-main branch or a pull request is opened, THE Infra_Workflow SHALL provision infrastructure using the dev Config_File
6. THE Infra_Workflow SHALL install the Terraform version specified in the Config_File (terraform_version field)
7. THE Infra_Workflow SHALL support manual triggering via workflow_dispatch

### Requirement 4: ML Training Pipeline Workflow

**User Story:** As an ML engineer, I want a GitHub Actions workflow that registers data assets, creates the training environment, and submits the Azure ML training pipeline, so that model training is automated through CI/CD.

#### Acceptance Criteria

1. WHEN the Training_Workflow is triggered, THE Training_Workflow SHALL register the training data asset using the Azure CLI ml extension with the data definition from `mlops/azureml/train/data.yml`
2. WHEN the Training_Workflow is triggered, THE Training_Workflow SHALL register the training environment using the Azure CLI ml extension with the environment definition from `mlops/azureml/train/train-env.yml`
3. WHEN the Training_Workflow is triggered, THE Training_Workflow SHALL create or verify the compute cluster (cpu-cluster, Standard_DS3_v2, 0-4 instances, low_priority) in the AML_Workspace
4. WHEN data asset, environment, and compute are ready, THE Training_Workflow SHALL submit the Azure ML pipeline job defined in `mlops/azureml/train/pipeline.yml`
5. WHEN the Training_Workflow targets the AML_Workspace, THE Training_Workflow SHALL resolve the resource group and workspace name from the selected Config_File
6. THE Training_Workflow SHALL support manual triggering via workflow_dispatch
7. WHEN a push occurs to the main branch, THE Training_Workflow SHALL target the prod AML_Workspace
8. WHEN a push occurs to a non-main branch, THE Training_Workflow SHALL target the dev AML_Workspace

### Requirement 5: Online Endpoint Deployment Workflow

**User Story:** As an ML engineer, I want a GitHub Actions workflow that deploys the trained model to a managed online endpoint, so that the model is available for real-time inference.

#### Acceptance Criteria

1. WHEN the Deployment_Workflow for online endpoints is triggered, THE Deployment_Workflow SHALL create or update the managed online endpoint using the definition from `mlops/azureml/deploy/online/online-endpoint.yml`
2. WHEN the online endpoint exists, THE Deployment_Workflow SHALL create or update the blue deployment using the definition from `mlops/azureml/deploy/online/online-deployment.yml`
3. WHEN the blue deployment is ready, THE Deployment_Workflow SHALL allocate 100% traffic to the blue deployment
4. THE Deployment_Workflow SHALL resolve the resource group and workspace name from the selected Config_File
5. THE Deployment_Workflow SHALL support manual triggering via workflow_dispatch
6. WHEN a push occurs to the main branch, THE Deployment_Workflow SHALL target the prod AML_Workspace
7. WHEN a push occurs to a non-main branch, THE Deployment_Workflow SHALL target the dev AML_Workspace

### Requirement 6: Batch Endpoint Deployment Workflow

**User Story:** As an ML engineer, I want a GitHub Actions workflow that deploys the trained model to a batch endpoint, so that the model is available for batch inference.

#### Acceptance Criteria

1. WHEN the Deployment_Workflow for batch endpoints is triggered, THE Deployment_Workflow SHALL create or verify the batch compute cluster (batch-cluster, STANDARD_DS3_V2, 0-5 instances, low_priority) in the AML_Workspace
2. WHEN the batch compute is ready, THE Deployment_Workflow SHALL create or update the batch endpoint using the definition from `mlops/azureml/deploy/batch/batch-endpoint.yml`
3. WHEN the batch endpoint exists, THE Deployment_Workflow SHALL create or update the batch deployment using the definition from `mlops/azureml/deploy/batch/batch-deployment.yml`
4. THE Deployment_Workflow SHALL resolve the resource group and workspace name from the selected Config_File
5. THE Deployment_Workflow SHALL support manual triggering via workflow_dispatch
6. WHEN a push occurs to the main branch, THE Deployment_Workflow SHALL target the prod AML_Workspace
7. WHEN a push occurs to a non-main branch, THE Deployment_Workflow SHALL target the dev AML_Workspace

### Requirement 7: Secrets and Variables Management

**User Story:** As a DevOps engineer, I want all sensitive configuration stored in GitHub secrets and non-sensitive configuration in GitHub variables, so that credentials are not exposed in workflow files or config files.

#### Acceptance Criteria

1. THE Workflow SHALL read Azure OIDC credentials (AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID) from GitHub secrets
2. THE Workflow SHALL read the Terraform client secret (ARM_CLIENT_SECRET) from GitHub secrets
3. THE Workflow SHALL NOT contain hardcoded Azure credentials, subscription IDs, tenant IDs, or client secrets in any workflow YAML file or Config_File
4. WHEN a required secret is missing, THE Workflow SHALL fail with a clear indication of which secret is not configured

### Requirement 8: Preservation of Existing Assets

**User Story:** As a DevOps engineer, I want the migration to only modify CI/CD orchestration files, so that existing ML pipelines, Terraform code, and data-science source code remain unchanged.

#### Acceptance Criteria

1. THE migration SHALL NOT modify any files in the `infrastructure/` directory
2. THE migration SHALL NOT modify any files in the `mlops/azureml/` directory
3. THE migration SHALL NOT modify any files in the `data-science/` directory
4. THE migration SHALL NOT modify any files in the `data/` directory
5. THE migration SHALL only create or modify files in `.github/workflows/` and the root-level Config_Files (`config-infra-dev.yml`, `config-infra-prod.yml`)
