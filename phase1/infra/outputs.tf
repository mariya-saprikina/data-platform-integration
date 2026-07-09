output "catalogs" {
  description = "Names of all provisioned catalogs"
  value       = { for k, v in databricks_catalog.env : k => v.name }
}

output "service_principal_id" {
  description = "Internal Databricks ID of the CI/CD service principal (used by Phase 2 bundle auth)"
  value       = data.databricks_service_principal.cicd.id
}
