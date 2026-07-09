# =============================================================================
# DEV — engineers have full read/write on raw and curated
# staging_wap is SP-only even in dev so the WAP pattern is testable here
# =============================================================================
resource "databricks_grants" "dev_catalog" {
  catalog = databricks_catalog.env["dev"].name

  grant {
    principal  = "account users"
    privileges = ["USE_CATALOG"]
  }

  grant {
    principal  = data.databricks_service_principal.cicd.application_id
    privileges = ["USE_CATALOG"]
  }
}

resource "databricks_grants" "dev_raw_curated" {
  for_each = toset(["raw", "curated"])

  schema = "${databricks_catalog.env["dev"].name}.${each.value}"

  grant {
    principal  = "account users"
    privileges = ["USE_SCHEMA", "SELECT", "MODIFY", "CREATE_TABLE"]
  }

  grant {
    principal  = data.databricks_service_principal.cicd.application_id
    privileges = ["USE_SCHEMA", "SELECT", "MODIFY", "CREATE_TABLE"]
  }

  depends_on = [databricks_schema.schemas]
}

resource "databricks_grants" "dev_staging_wap" {
  schema = "${databricks_catalog.env["dev"].name}.staging_wap"

  # account users intentionally have no grant here —
  # analysts must not query staging data mid-audit
  grant {
    principal  = data.databricks_service_principal.cicd.application_id
    privileges = ["USE_SCHEMA", "SELECT", "MODIFY", "CREATE_TABLE"]
  }

  depends_on = [databricks_schema.schemas]
}

# =============================================================================
# STAGING — humans read raw and curated, SP writes; staging_wap is SP-only
# =============================================================================
resource "databricks_grants" "staging_catalog" {
  catalog = databricks_catalog.env["staging"].name

  grant {
    principal  = "account users"
    privileges = ["USE_CATALOG"]
  }

  grant {
    principal  = data.databricks_service_principal.cicd.application_id
    privileges = ["USE_CATALOG"]
  }
}

resource "databricks_grants" "staging_raw_curated" {
  for_each = toset(["raw", "curated"])

  schema = "${databricks_catalog.env["staging"].name}.${each.value}"

  grant {
    principal  = "account users"
    privileges = ["USE_SCHEMA", "SELECT"]
  }

  grant {
    principal  = data.databricks_service_principal.cicd.application_id
    privileges = ["USE_SCHEMA", "SELECT", "MODIFY", "CREATE_TABLE"]
  }

  depends_on = [databricks_schema.schemas]
}

resource "databricks_grants" "staging_staging_wap" {
  schema = "${databricks_catalog.env["staging"].name}.staging_wap"

  grant {
    principal  = data.databricks_service_principal.cicd.application_id
    privileges = ["USE_SCHEMA", "SELECT", "MODIFY", "CREATE_TABLE"]
  }

  depends_on = [databricks_schema.schemas]
}

# =============================================================================
# PROD — humans read raw and curated; only SP can write; staging_wap is SP-only
# =============================================================================
resource "databricks_grants" "prod_catalog" {
  catalog = databricks_catalog.env["prod"].name

  grant {
    principal  = "account users"
    privileges = ["USE_CATALOG"]
  }

  grant {
    principal  = data.databricks_service_principal.cicd.application_id
    privileges = ["USE_CATALOG"]
  }
}

resource "databricks_grants" "prod_raw_curated" {
  for_each = toset(["raw", "curated"])

  schema = "${databricks_catalog.env["prod"].name}.${each.value}"

  grant {
    principal  = "account users"
    privileges = ["USE_SCHEMA", "SELECT"]
  }

  grant {
    principal  = data.databricks_service_principal.cicd.application_id
    privileges = ["USE_SCHEMA", "SELECT", "MODIFY", "CREATE_TABLE"]
  }

  depends_on = [databricks_schema.schemas]
}

resource "databricks_grants" "prod_staging_wap" {
  schema = "${databricks_catalog.env["prod"].name}.staging_wap"

  grant {
    principal  = data.databricks_service_principal.cicd.application_id
    privileges = ["USE_SCHEMA", "SELECT", "MODIFY", "CREATE_TABLE"]
  }

  depends_on = [databricks_schema.schemas]
}
