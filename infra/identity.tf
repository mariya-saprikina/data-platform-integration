data "databricks_service_principal" "cicd" {
  application_id = var.service_principal_app_id
}
