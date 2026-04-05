"""Tests validating config file structure for GitHub Actions MLOps CI/CD.

Validates:
- No ADO interpolation syntax (Property 1) — Requirements 1.1
- Derived resource names match naming convention (Property 2) — Requirements 1.2
- Base parameter values are preserved — Requirements 1.4
"""

import os

import pytest
import yaml

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
CONFIG_FILES = ["config-infra-dev.yml", "config-infra-prod.yml"]


def load_config(filename):
    path = os.path.join(REPO_ROOT, filename)
    with open(path, "r") as f:
        return yaml.safe_load(f)


# --- Property 1: No ADO interpolation syntax ---


@pytest.mark.parametrize("config_file", CONFIG_FILES)
def test_no_ado_interpolation_syntax(config_file):
    """No config value should contain the ADO $(variable) pattern.

    Validates: Requirements 1.1
    """
    config = load_config(config_file)
    for key, value in config.items():
        assert "$(" not in str(value), (
            f"{config_file}: key '{key}' contains ADO interpolation syntax: {value}"
        )


# --- Property 2: Derived resource names match naming convention ---


@pytest.mark.parametrize("config_file", CONFIG_FILES)
def test_resource_group_naming(config_file):
    """resource_group must equal rg-{namespace}-{postfix}{environment}.

    Validates: Requirements 1.2
    """
    config = load_config(config_file)
    expected = f"rg-{config['namespace']}-{config['postfix']}{config['environment']}"
    assert config["resource_group"] == expected


@pytest.mark.parametrize("config_file", CONFIG_FILES)
def test_aml_workspace_naming(config_file):
    """aml_workspace must equal mlw-{namespace}-{postfix}{environment}.

    Validates: Requirements 1.2
    """
    config = load_config(config_file)
    expected = f"mlw-{config['namespace']}-{config['postfix']}{config['environment']}"
    assert config["aml_workspace"] == expected


@pytest.mark.parametrize("config_file", CONFIG_FILES)
def test_key_vault_naming(config_file):
    """key_vault must equal kv-{namespace}-{postfix}{environment}.

    Validates: Requirements 1.2
    """
    config = load_config(config_file)
    expected = f"kv-{config['namespace']}-{config['postfix']}{config['environment']}"
    assert config["key_vault"] == expected


@pytest.mark.parametrize("config_file", CONFIG_FILES)
def test_container_registry_naming(config_file):
    """container_registry must equal cr{namespace}{postfix}{environment}.

    Validates: Requirements 1.2
    """
    config = load_config(config_file)
    expected = f"cr{config['namespace']}{config['postfix']}{config['environment']}"
    assert config["container_registry"] == expected


@pytest.mark.parametrize("config_file", CONFIG_FILES)
def test_storage_account_naming(config_file):
    """storage_account must equal st{namespace}{postfix}{environment}.

    Validates: Requirements 1.2
    """
    config = load_config(config_file)
    expected = f"st{config['namespace']}{config['postfix']}{config['environment']}"
    assert config["storage_account"] == expected


# --- Base parameter preservation (Requirements 1.4) ---


@pytest.mark.parametrize("config_file", CONFIG_FILES)
def test_base_parameters_preserved(config_file):
    """Base parameters must retain their original values.

    Validates: Requirements 1.4
    """
    config = load_config(config_file)
    assert config["namespace"] == "mlopsv2"
    assert str(config["postfix"]) == "0001"
    assert config["location"] == "eastus"


@pytest.mark.parametrize(
    "config_file,expected_env",
    [("config-infra-dev.yml", "dev"), ("config-infra-prod.yml", "prod")],
)
def test_environment_value(config_file, expected_env):
    """Each config file must have the correct environment value.

    Validates: Requirements 1.4
    """
    config = load_config(config_file)
    assert config["environment"] == expected_env


@pytest.mark.parametrize("config_file", CONFIG_FILES)
def test_terraform_backend_settings_preserved(config_file):
    """Terraform backend settings must be present and unchanged.

    Validates: Requirements 1.4
    """
    config = load_config(config_file)
    assert config["terraform_version"] == "1.3.6"
    assert config["terraform_st_container_name"] == "default"
    assert config["terraform_st_key"] == "mlops-tab"
