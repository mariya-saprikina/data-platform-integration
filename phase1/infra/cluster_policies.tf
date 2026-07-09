# =============================================================================
# Cluster Policies — Phase 1 Week 2
#
# A cluster policy is a set of constraints that Databricks enforces on any
# cluster created under that policy. Engineers pick a policy when creating
# a cluster — they cannot override the locked fields.
#
# Four policies are defined here:
#   1. dev-interactive  — for engineers running notebooks manually
#   2. job-non-prod     — for Databricks jobs in dev and staging environments
#   3. job-prod         — for Databricks jobs in production
#   4. no-unrestricted  — overrides the default policy to block unconstrained clusters
# =============================================================================

locals {
  # Pinned runtime version across all policies.
  # Updating this one value upgrades all clusters at next apply.
  spark_version = "17.3.x-scala2.13"
}

# =============================================================================
# Policy 1: dev-interactive
# Used by engineers for manual notebook work.
# Single node — no workers — so Spot doesn't apply (Spot is for worker pools).
# Hard 30-minute auto-termination prevents engineers leaving clusters running overnight.
# =============================================================================
resource "databricks_cluster_policy" "dev_interactive" {
  name = "dev-interactive"

  definition = jsonencode({
    # Lock the runtime version — prevents engineers choosing an untested runtime
    "spark_version" = {
      type  = "fixed"
      value = local.spark_version
    }

    # Single node: driver only, no workers
    "num_workers" = {
      type  = "fixed"
      value = 0
    }

    # These two flags together replicate what the "Single node" checkbox does:
    # profile=singleNode tells Databricks this is intentional single-node mode.
    # spark.master=local tells Spark to run executors on the driver itself.
    # Without both, num_workers=0 produces a broken cluster where Spark commands fail.
    "spark_conf.spark.databricks.cluster.profile" = {
      type  = "fixed"
      value = "singleNode"
    }

    "spark_conf.spark.master" = {
      type  = "fixed"
      value = "local[*, 4]"
    }

    # Force auto-termination after 30 minutes of inactivity.
    # This is the primary cost control for interactive clusters.
    "autotermination_minutes" = {
      type  = "fixed"
      value = 30
    }

    # Cost allocation tag — finance uses this to attribute spend to dev work
    "custom_tags.env" = {
      type  = "fixed"
      value = "dev"
    }

    # Restrict to smaller instance types for dev work
    "node_type_id" = {
      type   = "allowlist"
      values = ["m5.xlarge", "m5.large"]
    }

    # m5 instances don't support Photon — block it to prevent cluster creation failures
    "runtime_engine" = {
      type  = "fixed"
      value = "STANDARD"
    }

    # m5 has no local NVMe storage — EBS volumes required for shuffle data and spill
    "enable_elastic_disk" = {
      type  = "fixed"
      value = true
    }
  })
}

# =============================================================================
# Policy 2: job-non-prod
# Used by Databricks jobs running in dev and staging environments.
# Spot instances cut costs by 60-80% vs on-demand — acceptable for non-prod
# because a Spot interruption just causes the job to retry.
# =============================================================================
resource "databricks_cluster_policy" "job_non_prod" {
  name = "job-non-prod"

  definition = jsonencode({
    "spark_version" = {
      type  = "fixed"
      value = local.spark_version
    }

    # Spot instances for workers — the primary cost saving mechanism.
    # AWS can reclaim Spot instances with 2-minute warning; Databricks
    # handles this gracefully by retrying the interrupted task.
    "aws_attributes.availability" = {
      type  = "fixed"
      value = "SPOT_WITH_FALLBACK"
      # SPOT_WITH_FALLBACK: tries Spot first, falls back to on-demand if
      # no Spot capacity is available — prevents job failures during Spot droughts
    }

    # Hard cap on workers — prevents a misconfigured job from scaling to 50 nodes
    "num_workers" = {
      type  = "range"
      minValue = 1
      maxValue = 4
    }

    "autotermination_minutes" = {
      type  = "fixed"
      value = 30
    }

    "custom_tags.env" = {
      type  = "fixed"
      value = "non-prod"
    }

    "node_type_id" = {
      type   = "allowlist"
      values = ["m5.xlarge", "m5.2xlarge", "m5.4xlarge"]
    }

    "runtime_engine" = {
      type  = "fixed"
      value = "STANDARD"
    }

    "enable_elastic_disk" = {
      type  = "fixed"
      value = true
    }
  })
}

# =============================================================================
# Policy 3: job-prod
# Used by Databricks jobs running in production.
# On-demand instances only — Spot interruptions are not acceptable in prod
# because a mid-run interruption on a 4-hour job means starting over.
# Higher worker cap and longer auto-termination for large production workloads.
# =============================================================================
resource "databricks_cluster_policy" "job_prod" {
  name = "job-prod"

  definition = jsonencode({
    "spark_version" = {
      type  = "fixed"
      value = local.spark_version
    }

    # On-demand only in prod — reliability over cost
    "aws_attributes.availability" = {
      type  = "fixed"
      value = "ON_DEMAND"
    }

    "num_workers" = {
      type     = "range"
      minValue = 1
      maxValue = 10
    }

    # Longer window for production jobs that may run for hours
    "autotermination_minutes" = {
      type  = "fixed"
      value = 60
    }

    "custom_tags.env" = {
      type  = "fixed"
      value = "prod"
    }

    "node_type_id" = {
      type   = "allowlist"
      values = ["m5.xlarge", "m5.2xlarge", "m5.4xlarge", "m5.8xlarge"]
    }

    "runtime_engine" = {
      type  = "fixed"
      value = "STANDARD"
    }

    "enable_elastic_disk" = {
      type  = "fixed"
      value = true
    }
  })
}

# =============================================================================
# Policy 4: no-unrestricted
# Overwrites the built-in "Unrestricted" policy that Databricks ships with.
# The Unrestricted policy allows engineers to create any cluster with any
# settings — bypassing all cost controls. This policy blocks that.
#
# Setting max_clusters_per_user = 0 means no one can create a cluster under
# this policy. Engineers must choose one of the three policies above.
# =============================================================================
resource "databricks_cluster_policy" "no_unrestricted" {
  name               = "Unrestricted"
  max_clusters_per_user = 0

  definition = jsonencode({})
}

# =============================================================================
# Outputs — policy IDs referenced by Databricks Asset Bundles in Phase 2.
# The bundle's databricks.yml will reference these IDs to bind jobs to policies.
# =============================================================================
output "policy_dev_interactive" {
  value       = databricks_cluster_policy.dev_interactive.id
  description = "Use in bundle job_clusters for interactive dev work"
}

output "policy_job_non_prod" {
  value       = databricks_cluster_policy.job_non_prod.id
  description = "Use in bundle job_clusters for dev/staging pipeline jobs"
}

output "policy_job_prod" {
  value       = databricks_cluster_policy.job_prod.id
  description = "Use in bundle job_clusters for production pipeline jobs"
}
