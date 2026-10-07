# GAIA Complexity Report

- Commit: `703f8411871e88e10b1c45151ba035f6b1f35a8f`
- Files: `1`
- Callables: `67`
- Violations: `32` (`18` error, `14` warning)

## Top callable

| Path | Symbol | Line | Cog | Cyc | LOC | Nest | Params |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `backend/app/modules/network/services.py` | `run_network_scan` | 1158 | 195 | 101 | 268 | 3 | 5 |
| `backend/app/modules/network/services.py` | `_resolve_http_metadata` | 608 | 44 | 20 | 57 | 5 | 2 |
| `backend/app/modules/network/services.py` | `_collect_enrichment` | 741 | 43 | 32 | 42 | 2 | 2 |
| `backend/app/modules/network/services.py` | `_resolve_snmp_metadata_async` | 674 | 30 | 16 | 40 | 3 | 1 |
| `backend/app/modules/network/services.py` | `_run_nmap_scan` | 855 | 28 | 21 | 32 | 1 | 2 |
| `backend/app/modules/network/services.py` | `_build_diff` | 969 | 22 | 14 | 24 | 2 | 2 |
| `backend/app/modules/network/services.py` | `_run_nmap_arp_scan` | 823 | 21 | 15 | 26 | 2 | 1 |
| `backend/app/modules/network/services.py` | `list_network_devices` | 1437 | 17 | 14 | 78 | 3 | 11 |
| `backend/app/modules/network/services.py` | `_resolve_snmp_metadata` | 722 | 15 | 9 | 14 | 3 | 1 |
| `backend/app/modules/network/services.py` | `_resolve_mac_from_arp_cache` | 120 | 15 | 8 | 29 | 3 | 1 |
| `backend/app/modules/network/services.py` | `get_network_dashboard_summary` | 1530 | 14 | 15 | 17 | 0 | 1 |
| `backend/app/modules/network/services.py` | `discover_hosts` | 908 | 14 | 12 | 27 | 2 | 3 |
| `backend/app/modules/network/services.py` | `_guess_operating_system` | 238 | 11 | 10 | 13 | 1 | 1 |
| `backend/app/modules/network/services.py` | `_resolve_mac_via_gateway_arp` | 183 | 11 | 9 | 31 | 2 | 1 |
| `backend/app/modules/network/services.py` | `_resolve_mac_via_arp_helper` | 161 | 11 | 9 | 17 | 2 | 1 |
| `backend/app/modules/network/services.py` | `_recent_bypass_signal_tags_for_device` | 311 | 11 | 7 | 30 | 3 | 3 |
| `backend/app/modules/network/services.py` | `_parse_netbios_name` | 420 | 11 | 7 | 11 | 2 | 1 |
| `backend/app/modules/network/services.py` | `_guess_device_type` | 227 | 9 | 8 | 9 | 1 | 1 |
| `backend/app/modules/network/services.py` | `_profile_communities` | 464 | 8 | 8 | 8 | 1 | 2 |
| `backend/app/modules/network/services.py` | `_snmp_profile_communities` | 474 | 7 | 7 | 13 | 2 | 1 |
