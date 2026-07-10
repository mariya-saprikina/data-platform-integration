# =============================================================================
# ABAC — Column-level masking for PII-tagged data
#
# How it works:
#   1. A masking function is created once via SQL (run the statement below in
#      the Databricks SQL editor after terraform apply).
#   2. The function is attached to PII columns in Phase 3 by the governance
#      reaper script via the Databricks SDK — no manual SQL needed at that point.
#
# Why this function is not managed by Terraform:
#   databricks_sql_function is not supported in the provider version used here.
#   The function body never changes between environments so there is no drift
#   to manage — SQL is the right tool for a static one-time object.
#
# Why ABAC instead of schema-level grants:
#   Schema grants are all-or-nothing. ABAC lets an analyst query a table they
#   have SELECT on but still see '***MASKED***' in a PII column unless they
#   are in the pii-approved group. The grant controls table access; the mask
#   controls what they see in individual columns.
# =============================================================================

# =============================================================================
# ONE-TIME SETUP — run in the Databricks SQL editor after terraform apply.
# Repeat for staging.curated and prod.curated.
#
#   CREATE OR REPLACE FUNCTION dev.curated.pii_mask(col_value STRING)
#   RETURNS STRING
#   RETURN CASE
#     WHEN is_account_group_member('pii-approved') THEN col_value
#     ELSE '***MASKED***'
#   END;
#
# Verify it works (expect '***MASKED***' unless you are in pii-approved):
#   SELECT dev.curated.pii_mask('test@example.com');
#
# Attaching to a table column (Phase 3 automates this):
#   ALTER TABLE dev.curated.transactions
#   ALTER COLUMN email
#   SET MASK dev.curated.pii_mask;
# =============================================================================
