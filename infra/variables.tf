variable "databricks_host" {
  description = "Databricks workspace URL"
  type        = string
}

variable "databricks_token" {
  description = "PAT for local authentication — never commit the value"
  type        = string
  sensitive   = true
}

variable "service_principal_app_id" {
  description = "Application (client) ID of the CI/CD service principal"
  type        = string
  default     = "199fbde5-f42a-44e0-8288-16fdad2be10a"
}

variable "pii_group" {
  description = "Databricks group whose members may see unmasked PII columns"
  type        = string
  default     = "pii-approved"
}

variable "unity_catalog_bucket" {
  description = "S3 bucket name registered as an External Location for Unity Catalog managed table storage"
  type        = string
}
