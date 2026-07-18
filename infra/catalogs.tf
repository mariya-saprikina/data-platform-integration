locals {
  environments = {
    dev = {
      comment      = "Development — engineers have full read/write access"
      storage_root = "s3://${var.unity_catalog_bucket}/unity-catalog/dev"
    }
    staging = {
      comment      = "Integration testing — humans read-only, service principal writes"
      storage_root = "s3://${var.unity_catalog_bucket}/unity-catalog/staging"
    }
    prod = {
      comment      = "Production — humans read-only, service principal writes"
      storage_root = "s3://${var.unity_catalog_bucket}/unity-catalog/prod"
    }
  }

  # Schemas shared across all three catalogs.
  # staging_wap is intentionally excluded from analyst grants in grants.tf —
  # it is the invisible holding area used by the WAP circuit before promotion.
  schemas = ["raw", "staging", "intermediate", "marts", "staging_wap", "quarantine"]
}

resource "databricks_catalog" "env" {
  for_each = local.environments

  name         = each.key
  comment      = each.value.comment
  storage_root = each.value.storage_root

  lifecycle {
    prevent_destroy = true
  }
}

resource "databricks_schema" "schemas" {
  for_each = {
    for pair in setproduct(keys(local.environments), local.schemas) :
    "${pair[0]}_${pair[1]}" => {
      catalog = pair[0]
      schema  = pair[1]
    }
  }

  catalog_name = databricks_catalog.env[each.value.catalog].name
  name         = each.value.schema
  comment      = "${title(each.value.schema)} data zone"
}
