# VCF Automation (VCFA) integration — scoping

VCF Automation 9.x exposes the former Aria Automation / vRA 8.x API
surface, rebranded and bundled with the VCF platform. This document
enumerates every area the team wants covered, the API path each one
sits on, dependencies between areas, and a proposed PR sequence.

Nothing here is implemented yet — this is the design contract we'll
review before any `vcfa_*` code lands.

## Target API surface

VCF Automation is **not** one monolithic API. It's a set of distinct
microservices behind a CSP gateway, each rooted at its own path
prefix. The auth flow is shared.

### Authentication

Two-step bearer-token flow, identical to vRA/Aria 8.x:

```
POST /csp/gateway/am/api/login          # refreshToken acquire
     { "username": "...", "password": "...", "domain": "System Domain" }
  -> { "refresh_token": "..." }

POST /iaas/api/login                    # exchange for bearer
     { "refreshToken": "..." }
  -> { "token": "<bearer>" }

Authorization: Bearer <bearer>          # on every subsequent call
```

The bearer typically lives ~8h; the refresh token is the cacheable
identity. `utils/vcfa.py` will cache both per `(host, username)` and
re-acquire the bearer when the API returns 401.

### Pillar config

```yaml
saltext.vcf:
  vcfa:
    host: automation.vcf.example.com
    username: configadmin
    password: VMware123!
    domain: System Domain        # optional; default "System Domain"
    verify_ssl: false
    timeout: 60                  # optional; default 30
```

Many VCFA calls (deploy, blueprint compose, action runs) are
long-running but return quickly via async job ids — the per-request
timeout is for the HTTP roundtrip, not the underlying job.

### Service base paths

| Service        | Prefix              | Notes                              |
|----------------|---------------------|------------------------------------|
| IaaS           | `/iaas/api`         | Cloud accounts, zones, projects, blueprints, storage / network profiles, deployment policies, flavors, images |
| Catalog        | `/catalog/api`      | Catalog items + sources            |
| ABX            | `/abx/api`          | Actions, secrets, subscriptions    |
| vRO embedded   | `/vco/api`          | Packages, workflows, configuration elements, runs |
| Policy         | `/policy/api`       | Approval / lease / day-2 policies (overlaps with IaaS policies in places — verify) |
| Identity       | `/csp/gateway/am/api` + `/iam/api` | Custom roles, project users        |
| Properties     | `/properties-ui/api`| Property groups                    |

## Conventions

Follow the existing `saltext.vcf` shape:

- One client module per VCFA area: `saltext.vcf.clients.vcfa_<area>`
- One execution module per area: `saltext.vcf.modules.vcf_vcfa_<area>`
  (note the double `vcf_vcfa_` — first `vcf_` is the Salt prefix, second
  `vcfa_` is the namespace; mirrors `vcf_vcfops_*`).
- Shared connection helpers in `saltext.vcf.utils.vcfa` with
  `get_session`, `get_bearer`, `invalidate_token`, `api_get/post/put/patch/delete`.
- Each `api_*` accepts an optional `timeout=` kwarg (matching the
  convention added to `utils/vcenter.py`).
- Errors map the same way as other clients: `requests.HTTPError`
  propagates; resource-not-found 404s become `KeyError` or `None`
  depending on the caller idiom.
- Tests under `tests/unit/clients/test_vcfa_*.py`; fixtures register
  the two auth endpoints once via a new `vcfa_authed` fixture in
  `tests/conftest.py`.

## The 18 areas

For each area: VCFA API path, the operations we'll expose, and any
hard dependencies (areas that must exist before this one is usable).

### 1. Cloud accounts (`vcfa_cloud_account`)

| Op      | Method  | Path |
|---------|---------|------|
| list    | GET     | `/iaas/api/cloud-accounts` |
| get     | GET     | `/iaas/api/cloud-accounts/{id}` |
| create  | POST    | `/iaas/api/cloud-accounts-vsphere` (vSphere variant; one endpoint per cloud type) |
| update  | PATCH   | `/iaas/api/cloud-accounts-vsphere/{id}` |
| delete  | DELETE  | `/iaas/api/cloud-accounts/{id}` |

The create/update split by provider (`-vsphere`, `-aws`, `-azure`,
`-nsx-v`, `-nsx-t`, `-vmc`) is a known vRA wart. First PR focuses on
vSphere + NSX-T; the rest become `create_<provider>` variants later.

**Depends on:** nothing (foundation area).

### 2. Cloud zones (`vcfa_cloud_zone`)

| Op | Method | Path |
|---|---|---|
| list | GET | `/iaas/api/zones` |
| get | GET | `/iaas/api/zones/{id}` |
| create | POST | `/iaas/api/zones` |
| update | PATCH | `/iaas/api/zones/{id}` |
| delete | DELETE | `/iaas/api/zones/{id}` |

**Depends on:** cloud accounts (zones bind to a region of a cloud account).

### 3. Storage profiles (`vcfa_storage_profile`)

| Op | Method | Path |
|---|---|---|
| list / list_vsphere | GET | `/iaas/api/storage-profiles` / `/iaas/api/storage-profiles-vsphere` |
| get | GET | `/iaas/api/storage-profiles/{id}` |
| create_vsphere | POST | `/iaas/api/storage-profiles-vsphere` |
| update_vsphere | PATCH | `/iaas/api/storage-profiles-vsphere/{id}` |
| delete | DELETE | `/iaas/api/storage-profiles/{id}` |

Same provider-split as cloud accounts. **Depends on:** cloud accounts.

### 4. vRO package (`vcfa_vro_package`)

| Op | Method | Path |
|---|---|---|
| list | GET | `/vco/api/packages` |
| get | GET | `/vco/api/packages/{name}` |
| import | POST (multipart) | `/vco/api/packages` |
| export | GET (octet-stream) | `/vco/api/packages/{name}` |
| delete | DELETE | `/vco/api/packages/{name}` |

Multipart import means `utils.vcfa` needs an `api_post_multipart`
helper (not present elsewhere in the codebase yet — see Open Questions).

**Depends on:** nothing (vRO is independent).

### 5. IAM configuration (`vcfa_iam`)

CSP-side identity surface; the relevant endpoints differ by what
"IAM configuration" actually means. Likely candidates:

| Op | Path |
|---|---|
| list_organizations | GET `/csp/gateway/am/api/orgs` |
| list_users (org-scoped) | GET `/csp/gateway/am/api/orgs/{orgId}/users` |
| list_role_bindings | GET `/csp/gateway/am/api/loggedin/user/orgs/{orgId}/roles` |

**Open question:** confirm whether "IAM configuration" means org-level
SSO / domain config, or per-user role bindings, or both. The two surface
to different endpoints (`/iam/api/*` vs `/csp/gateway/am/api/*`).

**Depends on:** nothing.

### 6. Custom roles (`vcfa_custom_role`)

| Op | Method | Path |
|---|---|---|
| list | GET | `/iam/api/roles` (or `/csp/gateway/am/api/orgs/{orgId}/custom-roles` — verify) |
| get | GET | `/iam/api/roles/{id}` |
| create | POST | `/iam/api/roles` |
| update | PUT | `/iam/api/roles/{id}` |
| delete | DELETE | `/iam/api/roles/{id}` |

**Depends on:** IAM (org scope).

### 7. Project (`vcfa_project`)

| Op | Method | Path |
|---|---|---|
| list | GET | `/iaas/api/projects` |
| get | GET | `/iaas/api/projects/{id}` |
| create | POST | `/iaas/api/projects` |
| update | PATCH | `/iaas/api/projects/{id}` |
| delete | DELETE | `/iaas/api/projects/{id}` |

Project bodies include a `zoneAssignmentConfigurations` list, so the
create state must accept a zones param.

**Depends on:** cloud zones.

### 8. Project users (`vcfa_project_user`)

Project membership lives on the project document itself
(`administrators`, `members`, `viewers`, `supervisors` arrays). Two
shapes are possible:

| Op | Method | Path |
|---|---|---|
| list_members | GET | `/iaas/api/projects/{id}` (extract from response) |
| add_member | PATCH | `/iaas/api/projects/{id}` (merge into role array) |
| remove_member | PATCH | `/iaas/api/projects/{id}` (filter role array) |

The PATCH idempotency dance is something the client should handle;
the state module should support declarative role lists.

**Depends on:** project.

### 9. Cloud templates / blueprints (`vcfa_cloud_template`)

Cloud templates are the VCFA-era rebrand of vRA blueprints. The API
still uses `blueprint`.

| Op | Method | Path |
|---|---|---|
| list | GET | `/blueprint/api/blueprints` |
| get | GET | `/blueprint/api/blueprints/{id}` |
| create | POST | `/blueprint/api/blueprints` |
| update | PUT | `/blueprint/api/blueprints/{id}` |
| delete | DELETE | `/blueprint/api/blueprints/{id}` |
| versions list | GET | `/blueprint/api/blueprints/{id}/versions` |
| version create (release) | POST | `/blueprint/api/blueprints/{id}/versions` |

**Depends on:** project (blueprints belong to a project).

### 10. vRO configuration elements (`vcfa_vro_config_element`)

| Op | Method | Path |
|---|---|---|
| list | GET | `/vco/api/configurations` |
| get | GET | `/vco/api/configurations/{id}` |
| create | POST | `/vco/api/configurations` |
| update | PUT | `/vco/api/configurations/{id}` |
| delete | DELETE | `/vco/api/configurations/{id}` |
| set_attribute | PUT | `/vco/api/configurations/{id}/attributes/{name}` |

**Depends on:** nothing (vRO is independent).

### 11. Resource actions (`vcfa_resource_action`)

Day-2 actions registered against deployment resources. These bridge
to ABX or vRO workflows.

| Op | Method | Path |
|---|---|---|
| list | GET | `/form-service/api/resources` (verify) — actions are a sub-resource |
| get | GET | `/form-service/api/resources/{id}/actions/{actionId}` |

**Open question:** the public-facing "Resource Actions" UI tab seems
to live behind `/form-service` in vRA 8.x; in VCFA 9.x it may have
moved. Verify before implementation.

**Depends on:** ABX actions and/or vRO workflows (the action body
references the underlying runnable).

### 12. Workflow runs (`vcfa_workflow_run`)

vRO workflow execution surface.

| Op | Method | Path |
|---|---|---|
| list | GET | `/vco/api/workflows/{wfId}/executions` |
| get | GET | `/vco/api/workflows/{wfId}/executions/{runId}` |
| start | POST | `/vco/api/workflows/{wfId}/executions` |
| cancel | POST | `/vco/api/workflows/{wfId}/executions/{runId}/state` |
| logs | GET | `/vco/api/workflows/{wfId}/executions/{runId}/logs` |

**Depends on:** vRO packages (workflows live inside packages).

### 13. Catalog (`vcfa_catalog`)

| Op | Method | Path |
|---|---|---|
| list_items | GET | `/catalog/api/items` |
| get_item | GET | `/catalog/api/items/{id}` |
| request_item | POST | `/catalog/api/items/{id}/request` |
| list_sources | GET | `/catalog/api/sources` |
| create_source | POST | `/catalog/api/sources` |
| update_source | PATCH | `/catalog/api/sources/{id}` |
| delete_source | DELETE | `/catalog/api/sources/{id}` |

**Depends on:** projects (catalog source `projectId`), blueprints /
ABX actions / vRO workflows (whatever the source binds to).

### 14. Policies (`vcfa_policy`)

VCFA policy types include approval, lease, day-2 action, deployment
limit, and resource quota.

| Op | Method | Path |
|---|---|---|
| list | GET | `/policy/api/policies` |
| get | GET | `/policy/api/policies/{id}` |
| create | POST | `/policy/api/policies` |
| update | PUT | `/policy/api/policies/{id}` |
| delete | DELETE | `/policy/api/policies/{id}` |
| list_types | GET | `/policy/api/types` |

Body shape varies by `typeId` — pass through as an opaque dict; state
module should validate against a known type set.

**Depends on:** project (most policies are project-scoped).

### 15. Action secret configuration (`vcfa_action_secret`)

| Op | Method | Path |
|---|---|---|
| list | GET | `/abx/api/resources/action-secrets` |
| get | GET | `/abx/api/resources/action-secrets/{id}` |
| create | POST | `/abx/api/resources/action-secrets` |
| update | PUT | `/abx/api/resources/action-secrets/{id}` |
| delete | DELETE | `/abx/api/resources/action-secrets/{id}` |

**Depends on:** project (secret scope).

### 16. Action configuration (`vcfa_action`)

ABX (Action Based Extensibility) — serverless code attached to
deployment events.

| Op | Method | Path |
|---|---|---|
| list | GET | `/abx/api/resources/actions` |
| get | GET | `/abx/api/resources/actions/{id}` |
| create | POST | `/abx/api/resources/actions` |
| update | PUT | `/abx/api/resources/actions/{id}` |
| delete | DELETE | `/abx/api/resources/actions/{id}` |
| run | POST | `/abx/api/resources/actions/{id}/run` |
| list_runs | GET | `/abx/api/resources/actions/{id}/action-runs` |

**Depends on:** project, action secrets (referenced from action body).

### 17. Action subscription (`vcfa_action_subscription`)

Hooks that fire an Action or vRO workflow on a deployment event.

| Op | Method | Path |
|---|---|---|
| list | GET | `/event-broker/api/subscriptions` |
| get | GET | `/event-broker/api/subscriptions/{id}` |
| create | POST | `/event-broker/api/subscriptions` |
| update | PUT | `/event-broker/api/subscriptions/{id}` |
| delete | DELETE | `/event-broker/api/subscriptions/{id}` |
| list_event_topics | GET | `/event-broker/api/event-topics` |

**Depends on:** project, actions (subscription `runnableId` references
an action or vRO workflow id).

### 18. Deploy network profiles (`vcfa_network_profile`)

| Op | Method | Path |
|---|---|---|
| list | GET | `/iaas/api/network-profiles` |
| get | GET | `/iaas/api/network-profiles/{id}` |
| create | POST | `/iaas/api/network-profiles` |
| update | PATCH | `/iaas/api/network-profiles/{id}` |
| delete | DELETE | `/iaas/api/network-profiles/{id}` |

**Depends on:** cloud accounts, cloud zones.

## Dependency graph

```
cloud_account
  └── cloud_zone
        ├── project
        │     ├── project_user
        │     ├── cloud_template
        │     ├── policy
        │     ├── catalog
        │     ├── action_secret
        │     │     └── action
        │     │           └── action_subscription
        │     └── resource_action
        ├── storage_profile
        └── network_profile

vro_package
  ├── vro_config_element
  └── workflow_run

iam
  └── custom_role
```

vRO and IAM are independent sub-trees; the IaaS-rooted tree drives
the rest.

## Proposed PR sequence

Each PR aims for ~1 utility + 2–4 client/module pairs, tests, docs.
Picked to land dependencies first and to surface foundational
patterns (auth caching, multipart, etc.) on small reviewable PRs.

| PR  | Areas | Why first |
|-----|-------|-----------|
| 1   | `utils/vcfa` (auth + session), `vcfa_cloud_account`, `vcfa_cloud_zone` | Foundation — locks the auth pattern, error mapping, test fixture shape. |
| 2   | `vcfa_project`, `vcfa_project_user` | Most other areas depend on projects. |
| 3   | `vcfa_storage_profile`, `vcfa_network_profile` | Both small, both IaaS, complete the IaaS profile cluster. |
| 4   | `vcfa_cloud_template` (blueprints + versions) | Larger; pulls in blueprint version state. |
| 5   | `vcfa_policy`, `vcfa_catalog` | Project-scoped configuration. |
| 6   | `vcfa_vro_package`, `vcfa_vro_config_element`, `workflow_run` | vRO sub-tree; PR 6 introduces the multipart helper. |
| 7   | `vcfa_action_secret`, `vcfa_action`, `vcfa_action_subscription` | ABX sub-tree; deps in PR 1, 6 already in. |
| 8   | `vcfa_resource_action` | Last because the API path is the least certain (see Open Questions). |
| 9   | `vcfa_iam`, `vcfa_custom_role` | Identity surface; landing it last avoids blocking the IaaS work if the CSP API shifts. |

Estimate: ~9 PRs, 2–4 days of focused work each. Total elapsed ~2–3
weeks if reviews land same-day.

## Open questions

1. **Multipart uploads** — vRO package import is multipart/form-data;
   no `utils/vcf*` helper supports that today. PR 6 will add an
   `api_post_multipart` helper to `utils/vcfa`. Should it live in
   `utils/vcfa` only, or move to a shared `utils/_http.py`?
2. **Resource actions vs ABX actions** — "Resource Actions
   configuration" might mean the *registration* of an action against a
   resource type (vRA UI: "Resource Actions" tab), or the
   day-2-action policy that binds them to a project. Confirm which
   surface you want, or whether both are needed.
3. **IAM scope** — does "IAM configuration" include org-level domain
   binding (SSO/AD provider configuration) or only role bindings? The
   former lives at `/csp/gateway/identity`, the latter at
   `/csp/gateway/am`.
4. **Policy overlap** — IaaS policies (`/iaas/api/policies/...`) and
   the central policy service (`/policy/api/policies`) overlap on a
   handful of types. Verify which surface is canonical in 9.x.
5. **Async deploy / catalog request** — `request_item` returns a
   deployment id; do we want a `wait_for_deployment` helper that
   polls `/deployment/api/deployments/{id}`, similar to
   `vim.wait_for_task`?
6. **State modules** — every area listed above is "configuration",
   suggesting Salt state modules. The above is the *execution* layer
   only; states (`vcf_vcfa_*` state files with `present` / `absent`)
   add ~equal volume of code. Want them in the same PR per area, or
   defer to a follow-up PR after the execution-layer PR merges?

## Out of scope (for this rollout)

- Day-2 deployment operations beyond what falls out of `vcfa_action`
  / `workflow_run` (e.g. resize VM, attach disk) — these are accessed
  through the action surface and don't need their own modules.
- Property groups (`/properties-ui/api/...`) — not on the list.
- Code Stream (`/pipeline/api/...`) — also not on the list.
- Service Broker as a separate surface — catalog already covers
  it.

If any of the above turn out to be needed, they slot in as follow-up
PRs after the 9 above.
