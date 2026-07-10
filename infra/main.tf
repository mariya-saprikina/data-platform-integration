terraform {
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.65"
    }
  }
}

# PAT auth for local development.
# Phase 2 will replace this with OAuth M2M when GitHub Actions runs the deploy.
provider "databricks" {
  host  = var.databricks_host
  token = var.databricks_token
}
