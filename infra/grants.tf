# =============================================================================
# DEV — engineers have full read/write on medallion schemas
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

resource "databricks_grants" "dev_dbt_schemas" {
  for_each = toset(["bronze", "silver", "gold"])

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

resource "databricks_grants" "dev_quarantine" {
  schema = "${databricks_catalog.env["dev"].name}.quarantine"

  # SP-only — quarantine holds failed WAP runs, not for analyst access
  # schemas do not inherit prevent_destroy from the catalog resource
  grant {
    principal  = data.databricks_service_principal.cicd.application_id
    privileges = ["USE_SCHEMA", "SELECT", "MODIFY", "CREATE_TABLE"]
  }

  depends_on = [databricks_schema.schemas]
}

# =============================================================================
# STAGING — humans read-only on all medallion schemas, SP writes; staging_wap SP-only
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

resource "databricks_grants" "staging_dbt_schemas" {
  for_each = toset(["bronze", "silver", "gold"])

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
# PROD — humans read-only; only SP can write; staging_wap is SP-only
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

resource "databricks_grants" "prod_dbt_schemas" {
  for_each = toset(["bronze", "silver", "gold"])

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

# =============================================================================
# QUARANTINE — SP-only in all envs; holds failed WAP runs, never analyst-visible
# Note: schemas do not inherit prevent_destroy from the catalog resource
# =============================================================================
resource "databricks_grants" "staging_quarantine" {
  schema = "${databricks_catalog.env["staging"].name}.quarantine"

  grant {
    principal  = data.databricks_service_principal.cicd.application_id
    privileges = ["USE_SCHEMA", "SELECT", "MODIFY", "CREATE_TABLE"]
  }

  depends_on = [databricks_schema.schemas]
}

resource "databricks_grants" "prod_quarantine" {
  schema = "${databricks_catalog.env["prod"].name}.quarantine"

  grant {
    principal  = data.databricks_service_principal.cicd.application_id
    privileges = ["USE_SCHEMA", "SELECT", "MODIFY", "CREATE_TABLE"]
  }

  depends_on = [databricks_schema.schemas]
}
