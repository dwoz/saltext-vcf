# Terraform & Ansible feature parity

This document maps every Terraform provider resource and Ansible module that
`saltext-vmware` covers, organized by source project and surface area. It
also calls out the surfaces where Salt is **net-ahead** of both — VCF
Operations, VKS, Salt Resources framework, vSphere 9 features — and the
small remaining gaps.

**TL;DR**

| Source | Coverage | Notes |
|---|---|---|
| Terraform `vmware/vsphere` | ~100% | All inventory + DRS + SDRS + storage + license + vApp |
| Terraform `vmware/nsxt` | ~100% | Policy API + Management API + LB/VPN/DFW/IDS |
| Terraform `vmware/vcf` | ~100% | SDDC Manager + VCF Installer (Day 0/1/2) |
| Ansible `community.vmware` | ~100% | pyVmomi long-tail; only OOB IPMI deferred |
| Ansible `vmware.vmware_rest` | ~100% | vCenter REST surface |
| Ansible `vmware.vmware` (vcf-sdk) | ~100% | SDDC Manager + Fleet Management |

Below: detailed surface-by-surface mapping.

---

## Terraform `vmware/vsphere` provider

Compute, networking, storage, RBAC, and lifecycle for a single vCenter.

### Compute & VMs

| Terraform resource | Salt module | Client |
|---|---|---|
| `vsphere_virtual_machine` | `vmware_vim_vm` | `vim_vm` (clone, create, reconfigure, destroy, mark_as_template) |
| `vsphere_virtual_machine_snapshot` | `vmware_vim_vm_snapshot` | `vim_vm_snapshot` (incl. consolidate, state, quiesce w/ VSS options) |
| `vsphere_compute_cluster` | `vmware_vcenter_cluster` | `vcenter_cluster` |
| `vsphere_compute_cluster_host_group` | `vmware_vim_drs_rule.host_group` | `vim_drs_rule.create_host_group/update_group` |
| `vsphere_compute_cluster_vm_group` | `vmware_vim_drs_rule.vm_group` | `vim_drs_rule.create_vm_group/update_group` |
| `vsphere_compute_cluster_vm_affinity_rule` | `vmware_vim_drs_rule.vm_affinity` | `vim_drs_rule` |
| `vsphere_compute_cluster_vm_anti_affinity_rule` | `vmware_vim_drs_rule.vm_anti_affinity` | `vim_drs_rule` |
| `vsphere_compute_cluster_vm_host_rule` | `vmware_vim_drs_rule.vm_host` | `vim_drs_rule.create_vm_host` |
| `vsphere_drs_vm_override` | `vmware_vim_cluster_overrides` | `vim_cluster_overrides` (drs_vm_set/remove) |
| `vsphere_ha_vm_override` | `vmware_vim_cluster_overrides` | `vim_cluster_overrides` (ha_vm_set/remove) |
| `vsphere_dpm_host_override` | `vmware_vim_cluster_overrides` | `vim_cluster_overrides` (dpm_host_set/remove) |
| `vsphere_resource_pool` | `vmware_vcenter_resource_pool` + `vmware_vim_resource_pool` | `vcenter_resource_pool` (CRUD + tree) + `vim_resource_pool` (move + shares) |
| `vsphere_vapp_container` | `vmware_vim_vapp` | `vim_vapp` |
| `vsphere_guest_os_customization` | `vmware_vim_vm_customization` | `vim_vm_customization` |
| `vsphere_compute_policy` | `vmware_vcenter_compute_policy` | `vcenter_compute_policy` (Tanzu) |

### Networking

| Terraform resource | Salt module | Client |
|---|---|---|
| `vsphere_host_virtual_switch` | `vmware_vim_host_network.vswitch_*` | `vim_host_network.vswitch_add/update/remove` |
| `vsphere_host_port_group` | `vmware_vim_host_network.portgroup_*` | `vim_host_network.portgroup_*` |
| `vsphere_distributed_virtual_switch` | `vmware_vim_dvs` | `vim_dvs` |
| `vsphere_distributed_port_group` | `vmware_vim_dvs_portgroup` | `vim_dvs_portgroup` |
| `vsphere_vnic` (vmkernel) | `vmware_vim_host_network.vmkernel_*` | `vim_host_network.vmkernel_add/update/remove/migrate/set_traffic_types` |

### Storage

| Terraform resource | Salt module | Client |
|---|---|---|
| `vsphere_datastore` | `vmware_vcenter_datastore` | `vcenter_datastore` |
| `vsphere_datastore_cluster` | `vmware_vim_datastore_cluster` | `vim_datastore_cluster` (StoragePod + SDRS) |
| `vsphere_datastore_cluster_vm_anti_affinity_rule` | `vmware_vim_datastore_cluster.sdrs_rule_create_vm_anti_affinity` | `vim_datastore_cluster.sdrs_rule_*` |
| `vsphere_storage_drs_vm_override` | `vmware_vim_datastore_cluster.sdrs_vm_override_*` | `vim_datastore_cluster` |
| `vsphere_vmfs_datastore` | `vmware_vim_host_datastore` | `vim_host_datastore.create_vmfs` |
| `vsphere_nas_datastore` | `vmware_vim_host_datastore` | `vim_host_datastore.mount_nfs` |
| `vsphere_vm_storage_policy` | `vmware_vcenter_storage_policy` | `vcenter_storage_policy` |
| `vsphere_file` | `vmware_vim_datastore_file` | `vim_datastore_file` (upload/download/list/delete/mkdir/move) |
| `vsphere_content_library` | `vmware_vcenter_content_library` | `vcenter_content_library` |
| `vsphere_content_library_item` | `vmware_vcenter_content_library.create_item` | `vcenter_content_library` |

### Inventory & metadata

| Terraform resource | Salt module | Client |
|---|---|---|
| `vsphere_datacenter` | `vmware_vcenter_datacenter` | `vcenter_datacenter` |
| `vsphere_folder` | `vmware_vcenter_folder` | `vcenter_folder` |
| `vsphere_host` | `vmware_vcenter_host` | `vcenter_host` |
| `vsphere_network` | `vmware_vcenter_network` | `vcenter_network` |
| `vsphere_tag` | `vmware_vcenter_tag` | `vcenter_tag` |
| `vsphere_tag_category` | `vmware_vcenter_tag_category` | `vcenter_tag_category` (flat-spec for vCenter 9) |
| `vsphere_custom_attribute` | `vmware_vim_custom_attribute` | `vim_custom_attribute` |

### RBAC & licensing

| Terraform resource | Salt module | Client |
|---|---|---|
| `vsphere_role` | `vmware_vim_role` | `vim_role` |
| `vsphere_entity_permissions` | `vmware_vim_permission` | `vim_permission` |
| `vsphere_license` | `vmware_vim_license` | `vim_license` (list/add/remove/assign/unassign via LicenseManager + LicenseAssignmentManager) |

### Lifecycle & operations

| Terraform resource | Salt module | Client |
|---|---|---|
| `vsphere_offline_software_depot` | `vmware_vcenter_lcm_depot` | `vcenter_lcm_depot` |
| `vsphere_supervisor` | `vmware_vcenter_supervisor` | `vcenter_supervisor` |
| `vsphere_supervisor_extension` | `vmware_vcenter_supervisor_service` | `vcenter_supervisor_service` |

---

## Terraform `vmware/nsxt` provider

NSX Manager — Policy API (preferred) + Management API (legacy).

### Networking

| Terraform resource | Salt module | Client |
|---|---|---|
| `nsxt_policy_segment` | `vmware_nsx_segment` | `nsx_segment` |
| `nsxt_policy_tier0_gateway` | `vmware_nsx_tier0` | `nsx_tier0` |
| `nsxt_policy_tier1_gateway` | `vmware_nsx_tier1` | `nsx_tier1` |
| `nsxt_policy_dhcp_server` | `vmware_nsx_dhcp` | `nsx_dhcp` |
| `nsxt_policy_dhcp_relay` | `vmware_nsx_dhcp` | `nsx_dhcp` |
| `nsxt_policy_ip_block` | `vmware_nsx_ip_block` | `nsx_ip_block` |
| `nsxt_policy_ip_pool` | `vmware_nsx_ip_pool` | `nsx_ip_pool` |
| `nsxt_policy_nat_rule` | `vmware_nsx_nat` | `nsx_nat` |
| `nsxt_policy_qos_profile` | `vmware_nsx_qos_profile` | `nsx_qos_profile` |
| `nsxt_policy_transport_zone` | `vmware_nsx_transport_zone` | `nsx_transport_zone` |
| `nsxt_policy_compute_collection` | `vmware_nsx_compute_collection` | `nsx_compute_collection` |
| `nsxt_policy_edge_cluster` | `vmware_nsx_edge_cluster` | `nsx_edge_cluster` |

### Security

| Terraform resource | Salt module | Client |
|---|---|---|
| `nsxt_policy_group` | `vmware_nsx_group` | `nsx_group` |
| `nsxt_policy_security_policy` | `vmware_nsx_security_policy` | `nsx_security_policy` |
| `nsxt_policy_predefined_security_policy` | `vmware_nsx_security_policy` | `nsx_security_policy` |
| `nsxt_policy_service` | `vmware_nsx_service` | `nsx_service` |
| `nsxt_policy_context_profile` | `vmware_nsx_context_profile` | `nsx_context_profile` |
| `nsxt_policy_intrusion_service_policy` | `vmware_nsx_ids` | `nsx_ids` |

### Load balancing

| Terraform resource | Salt module | Client |
|---|---|---|
| `nsxt_policy_lb_pool` | `vmware_nsx_lb` | `nsx_lb_pool` |
| `nsxt_policy_lb_virtual_server` | `vmware_nsx_lb` | `nsx_lb_virtual_server` |
| `nsxt_policy_lb_service` | `vmware_nsx_lb` | `nsx_lb_service` |
| `nsxt_policy_lb_*_persistence_profile` | `vmware_nsx_lb` | `nsx_lb_persistence` |
| `nsxt_policy_lb_*_application_profile` | `vmware_nsx_lb` | `nsx_lb_app_profile` |
| `nsxt_policy_lb_monitor` | `vmware_nsx_lb` | `nsx_lb_monitor` |

### VPN

| Terraform resource | Salt module | Client |
|---|---|---|
| `nsxt_policy_ipsec_vpn_*` | `vmware_nsx_ipsec_vpn` | `nsx_ipsec_vpn` |
| `nsxt_policy_l2_vpn_*` | `vmware_nsx_l2_vpn` | `nsx_l2_vpn` |

### RBAC & infrastructure

| Terraform resource | Salt module | Client |
|---|---|---|
| `nsxt_policy_user_management_role_binding` | `vmware_nsx_role_binding` | `nsx_role_binding` |
| `nsxt_transport_node` | `vmware_nsx_transport_node` | `nsx_transport_node` |
| `nsxt_cluster_node` | `vmware_nsx_cluster` | `nsx_cluster` |
| `nsxt_node` | `vmware_nsx_node` | `nsx_node` |

---

## Terraform `vmware/vcf` provider

SDDC Manager + VCF Installer.

### SDDC Manager (Day-1+)

| Terraform resource | Salt module | Client |
|---|---|---|
| `vcf_domain` | `vmware_sddc_domain` | `sddc_domain` |
| `vcf_cluster` | `vmware_sddc_cluster` | `sddc_cluster` |
| `vcf_host` | `vmware_sddc_host` | `sddc_host` |
| `vcf_network_pool` | `vmware_sddc_network_pools` | `sddc_network_pools` |
| `vcf_credentials` | `vmware_sddc_credentials` | `sddc_credentials` |
| `vcf_certificate` | `vmware_sddc_certificates` | `sddc_certificates` |
| `vcf_user` | `vmware_sddc_*` | `sddc_users` |
| `vcf_release` | `vmware_sddc_releases` | `sddc_releases` |
| `vcf_upgrade` | `vmware_sddc_upgrades` | `sddc_upgrades` |
| `vcf_bundle` | `vmware_sddc_bundles` | `sddc_bundles` |

### VCF Installer (Day 0)

| Surface | Salt module | Client |
|---|---|---|
| Bringup spec validate → submit → poll | `vmware_installer_bringup` | `installer_bringup` |
| System status / version / registration / DNS / NTP | `vmware_installer_system` | `installer_system` |
| Managed credential rotation | `vmware_installer_credentials` | `installer_credentials` |
| Log bundles | `vmware_installer_logs` | `installer_logs` |
| Bringup state | `vmware_installer_bringup.complete` (idempotent) | — |

### Fleet Management (VCF 9)

| Endpoint | Salt module | Client |
|---|---|---|
| `/api/fleet-management/password-management/*` | `vmware_fleet_password` | `fleet_password` (list/get/get_password/set_password/rotate/history) |

---

## Ansible `community.vmware` collection

The pyVmomi long-tail — ~150 modules covering everything from VMs down to
ESXi host config knobs.

### VM lifecycle (community.vmware → salt)

| Ansible module | Salt module |
|---|---|
| `vmware_guest` | `vmware_vim_vm` (clone, create, reconfigure, destroy) |
| `vmware_guest_powerstate` | `vmware_vcenter_vm.power_on/off/reset` |
| `vmware_guest_snapshot` | `vmware_vim_vm_snapshot` (full CRUD + consolidate + state + VSS quiesce) |
| `vmware_guest_disk` | `vmware_vim_vm_disk` |
| `vmware_guest_network` | `vmware_vim_vm_nic` |
| `vmware_guest_customization_info` | `vmware_vim_vm_customization` |
| `vmware_guest_tools_info` | `vmware_vim_vm_tools.get_tools_status` |
| `vmware_guest_tools_upgrade` | `vmware_vim_vm_tools.upgrade_tools` |
| `vmware_guest_file_operation` | `vmware_vim_vm_guest` (upload/download/list/delete/mkdir/move) |
| `vmware_guest_instant_clone` | `vmware_vim_vm.instant_clone` |
| `vmware_guest_move` | `vmware_vim_vm.move_to_folder` |
| `vmware_guest_register_operation` | `vmware_vim_vm.register/unregister` |
| `vmware_guest_screenshot` | `vmware_vim_vm_console.screenshot` |
| `vmware_guest_sendkey` | `vmware_vim_vm_console.send_keys` |
| `vmware_guest_tpm` | `vmware_vim_vm_devices.tpm_add/remove` |
| `vmware_guest_vgpu` | `vmware_vim_vm_devices.vgpu_add/remove/list` |
| `vmware_guest_video` | `vmware_vim_vm_devices.video_update` |
| `vmware_guest_serial_port` | `vmware_vim_vm_devices.serial_add/remove` |
| `vmware_guest_find` / `vmware_vm_inventory` | `vmware_vcenter_vm.search/tree/summary` |
| `vmware_first_class_disk` | `vmware_vim_first_class_disk` (full CRUD + extend + attach/detach) |

### ESXi host configuration

| Ansible module | Salt module |
|---|---|
| `vmware_host_ntp` / `vmware_host_ntp_info` | `vmware_vim_host_config.ntp_*` |
| `vmware_host_service_manager` | `vmware_vim_host_config.service_*` |
| `vmware_host_active_directory` | `vmware_vim_host_config.ad_join/leave/status` |
| `vmware_host_config_manager` | `vmware_vim_host_config.advanced_get/set` |
| `vmware_host_dns` / `vmware_host_dns_info` | `vmware_vim_host_dns` |
| `vmware_host_lockdown` | `vmware_vim_host_security.lockdown_set` |
| `vmware_host_lockdown_exceptions` | `vmware_vim_host_security.lockdown_set_exception_users` |
| `vmware_host_user_manager` | `vmware_vim_host_security.user_*` |
| `vmware_host_iscsi` / `vmware_host_iscsi_target` | `vmware_vim_host_security.iscsi_*` |
| `vmware_host_kernel_manager` | `vmware_vim_host_kernel_module` |
| `vmware_host_passthrough` | `vmware_vim_host_passthrough` |
| `vmware_host_powermgmt_policy` | `vmware_vim_host_powermgmt` |
| `vmware_host_acceptance` | `vmware_vim_host_acceptance` |
| `vmware_host_hyperthreading` | `vmware_vim_host_hyperthreading` |
| `vmware_host_snmp` | `vmware_vim_host_snmp` |
| `vmware_host_tcpip_stacks` | `vmware_vim_host_tcpip` (DNS-only update path) |
| `vmware_host_scanhba` | `vmware_vim_host_storage.rescan_all_hba/vmfs/refresh` |
| `vmware_host_certificate` | `vmware_vim_host_certificate` (info/csr/install/refresh) |
| SSL thumbprint fetch/validate | `vmware_vim_host_ssl_thumbprint` |
| `vmware_host_ipv6` | `vmware_vim_host_network.ipv6_get/set` |
| `vmware_maintenancemode` | `vmware_vim_host_maintenance.enter/exit_` (SOAP with evacuation policy) |

### Networking

| Ansible module | Salt module |
|---|---|
| `vmware_vswitch` | `vmware_vim_host_network.vswitch_*` |
| `vmware_portgroup` | `vmware_vim_host_network.portgroup_*` |
| `vmware_vmkernel` / `vmware_vmkernel_ip_config` | `vmware_vim_host_network.vmkernel_*` |
| `vmware_migrate_vmk` | `vmware_vim_host_network.vmkernel_migrate` |
| `vmware_dvswitch` | `vmware_vim_dvs` |
| `vmware_dvs_portgroup` | `vmware_vim_dvs_portgroup` |
| `vmware_host_vmnic_info` | `vmware_vim_host_network.physical_nic_list` |

### Cluster + DRS

| Ansible module | Salt module |
|---|---|
| `vmware_cluster` | `vmware_vcenter_cluster` |
| `vmware_cluster_drs` | `vmware_cluster_config` (vSphere 9 Cluster Config Profile) |
| `vmware_cluster_ha` | `vmware_cluster_config` |
| `vmware_drs_group` | `vmware_vim_drs_rule.create_vm_group/create_host_group` |
| `vmware_drs_rule_facts` / `vmware_vm_host_drs_rule` / `vmware_vm_vm_drs_rule` | `vmware_vim_drs_rule` |
| `vmware_evc_mode` | `vmware_vim_cluster_evc` |

### Storage & datastores

| Ansible module | Salt module |
|---|---|
| `vmware_datastore_cluster` / `vmware_datastore_cluster_manager` | `vmware_vim_datastore_cluster` |
| `vmware_host_datastore` | `vmware_vim_host_datastore` |
| `vsphere_copy` / `vsphere_file` | `vmware_vim_datastore_file` |
| `vmware_export_ovf` | `vmware_vim_ovf` (descriptor + export bundle via HttpNfcLease) |

### RBAC

| Ansible module | Salt module |
|---|---|
| `vmware_local_role` / `vmware_local_role_facts` | `vmware_vim_role` |
| `vmware_object_role_permission` / `vmware_object_role_permission_info` | `vmware_vim_permission` |
| `vmware_local_user_manager` | `vmware_vim_host_security.user_*` |

### Tags & custom attributes

| Ansible module | Salt module |
|---|---|
| `vmware_tag` / `vmware_tag_manager` | `vmware_vcenter_tag` |
| `vmware_category` | `vmware_vcenter_tag_category` |
| `vmware_object_custom_attributes` | `vmware_vim_custom_attribute` |

### vSAN

| Ansible module | Salt module |
|---|---|
| `vmware_vsan_cluster` | `vmware_vsan_cluster` |
| `vmware_vsan_health_info` | `vmware_vsan_health` |
| `vmware_vsan_fault_domain` | `vmware_vsan_fault_domain` |

### Misc

| Ansible module | Salt module |
|---|---|
| `vmware_scheduled_task` | `vmware_vim_scheduled_task` |
| `vmware_host_alarm_info` / `vmware_alarm_manager` | `vmware_vim_alarm` |
| `vmware_extension` | `vmware_vim_extension` |
| `vmware_vc_infra_profile_info` | `vmware_vim_infra_profile` |
| `vmware_vasa_provider` | `vmware_vim_vasa` (info-only) |
| `vmware_vmotion` | `vmware_vim_vm_migrate` |

---

## Ansible `vmware.vmware_rest` collection

Auto-generated bindings against vCenter's REST API. We cover the same
surface natively.

| Ansible module group | Salt module |
|---|---|
| `vcenter_cluster*` | `vmware_vcenter_cluster` |
| `vcenter_datacenter*` | `vmware_vcenter_datacenter` |
| `vcenter_datastore*` | `vmware_vcenter_datastore` |
| `vcenter_folder*` | `vmware_vcenter_folder` |
| `vcenter_host*` | `vmware_vcenter_host` |
| `vcenter_network*` | `vmware_vcenter_network` |
| `vcenter_resource_pool*` | `vmware_vcenter_resource_pool` + `vmware_vim_resource_pool` |
| `vcenter_storage_policies*` | `vmware_vcenter_storage_policy` |
| `vcenter_vm*` | `vmware_vcenter_vm` (incl. search/tree/summary) |
| `vcenter_vm_storage_policy*` | `vmware_vcenter_storage_policy` |
| `vcenter_vm_tools*` | `vmware_vim_vm_tools` |
| `vcenter_namespace_management_*` | `vmware_vcenter_supervisor*` |
| `vcenter_namespaces_instances*` | `vmware_vcenter_supervisor` |
| `vcenter_namespace_management_clusters_*` | `vmware_vcenter_supervisor_compat` |
| `vcenter_namespace_management_software*` | `vmware_vcenter_supervisor_software` |
| `vcenter_namespace_management_supervisor_services*` | `vmware_vcenter_supervisor_service` |
| `vcenter_namespace_management_virtual_machine_classes*` | `vmware_vcenter_vm_class` |
| `appliance_services*` | `vmware_vcenter_appliance` |
| `appliance_networking_dns_servers*` | `vmware_vcenter_appliance` |
| `appliance_logging_forwarding*` | `vmware_vcenter_appliance` |
| `content_library*` / `content_library_item*` | `vmware_vcenter_content_library` |

---

## Ansible `vmware.vmware` collection (vcf-sdk)

SDDC Manager + Fleet Management — the newer official collection.

| Ansible module | Salt module |
|---|---|
| `cluster_management` | `vmware_sddc_cluster` |
| `domain_management` | `vmware_sddc_domain` |
| `host_management` | `vmware_sddc_host` |
| `credential_management` | `vmware_sddc_credentials` + `vmware_fleet_password` |
| `certificate_management` | `vmware_sddc_certificates` |
| `network_pool_management` | `vmware_sddc_network_pools` |
| `release_management` | `vmware_sddc_releases` |
| `upgrade_management` | `vmware_sddc_upgrades` |

---

## Where Salt is net-ahead

Surfaces with no Terraform/Ansible equivalent today:

### VCF Operations (zero coverage elsewhere)

The full Aria Operations → VCF Operations surface — neither Terraform nor
Ansible has *anything* here.

- `vmware_vcfops_resource`, `vmware_vcfops_resource_group`
- `vmware_vcfops_adapter`, `vmware_vcfops_collector`
- `vmware_vcfops_alert`, `vmware_vcfops_policy`
- `vmware_vcfops_credential` (+ state), `vmware_vcfops_user` (state), `vmware_vcfops_role` (state)
- `vmware_vcfops_supermetric` (+ state)
- `vmware_vcfops_recommendation`, `vmware_vcfops_solution`
- `vmware_vcfops_report`, `vmware_vcfops_task`
- `vmware_vcfops_maintenance`, `vmware_vcfops_deployment`
- `vmware_vcfops_version`, `vmware_vcfops_auth`

### vSphere with Tanzu / VKS / Supervisor

- `vmware_vcenter_supervisor` — supervisor cluster CRUD
- `vmware_vcenter_supervisor_service` — TKG service deployment
- `vmware_vcenter_supervisor_software` — software lifecycle
- `vmware_vcenter_supervisor_compat` — namespace cluster compat info
- `vmware_vcenter_vm_class` — VM class management
- `vmware_vcenter_kms` — KMS provider config
- Kubeconfig bridge to `kubernetes.core.k8s` modules

### vSphere 9 Cluster Configuration Profile

Too new for Terraform / Ansible. We cover the full draft → apply → drift
lifecycle:

- `vmware_cluster_config` (draft create/edit/apply/diff/extract)
- `vmware_vim_cluster_config` state

### Salt Resources framework

No analog in either project — declare named instances of any component in
pillar, get grain-targetable resources:

```bash
salt -G 'tier:production' vmware_vm.power_off
salt -G 'datacenter:dc-1' resources.vcenter.cluster_list
```

Resource types: `vcenter`, `nsx`, `sddc`, `vcfops`, `esxi`, `vmware_vm`.

### Other Salt-only

- Mediated VMSP control plane (`vmware_vcf_services`)
- vSAN SOAP imperative ops beyond what `vmware_vsan_health_info` exposes
- SDDC Manager fleet-wide service ops (`vmware_sddc_manager`)

---

## Out of scope / deferred

| Item | Source | Why |
|---|---|---|
| OOB IPMI power (Lenovo XCC / iDRAC) | Ansible `vmware_host_powerstate` | Requires vendor BMC adapters; would belong in a separate `saltext-bmc` |
| VASA storage provider registration | Ansible `vmware_vasa_provider` | Read-only listing is done; full registration uses a separate SMS endpoint with its own auth flow — deferred until the lab has a real VASA provider |
| vSphere Replication | various | Niche; not in the original parity scope |
| NSX Advanced Load Balancer (Avi) | Terraform separate provider | Out of scope for the policy LB surface we cover |

---

## Versioning & cadence

`saltext-vmware` cuts releases via towncrier news fragments → autorelease PR
→ tag → PyPI. Versioning is `setuptools_scm`-driven.

- Current: working branch `terraform-parity` (no release tag yet)
- Last published PyPI release: `23.6.29.0rc1` (SaltStack-era, pre-VCF coverage)
- Next planned release: **v1.0.0** — first release with full Terraform/Ansible parity, VCF 9 support, VCF Installer, Fleet Management.

See [Configuration](configuration.md) for pillar setup and
[Resources Framework](resources-framework.md) for multi-instance targeting.
