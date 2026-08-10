# GAIA Rete

> Regola modulo
> GAIA Rete usa il backend monolite condiviso in `backend/` con namespace canonico `app/modules/network/`.

## Scopo

Questa directory raccoglie documentazione e materiale di lavoro del modulo Rete.

## Runbook operativi

- `docs/SOPHOS_INTEGRATION_RUNBOOK.md`: integrazione Sophos XGS87 con GAIA Rete tramite syslog e SNMP.
- `docs/SOPHOS_SSL_VPN_OPENVPN_RUNBOOK.md`: accesso remoto a GAIA tramite Sophos SSL VPN e client OpenVPN per Windows/Android.

## Regole strutturali

- nessun backend separato per il modulo
- frontend condiviso sotto `frontend/src/app/network/`
- backend condiviso sotto `backend/app/modules/network/`
