# GAIA - Dizionario dati e relazioni

Documento generato dai modelli SQLAlchemy del backend. E pensato per spiegare le tabelle in modo semplice, non per sostituire le migrazioni o il codice.

- Tabelle rilevate: `3`
- Relazioni foreign key rilevate: `12`
- Fonte: `backend/app/db/base.py` e modelli importati dalla metadata SQLAlchemy

## Altro

Tabelle di supporto non assegnate a un dominio principale.

| Tabella | Spiegazione semplice | Chiave primaria | Colonne principali | Collegamenti in uscita | Collegamenti in entrata |
| --- | --- | --- | --- | --- | --- |
| `dotazioni_assets` | Contiene dati relativi a dotazioni assets. | id | asset_code, asset_type, name, description, brand, model, serial_number, imei | `assigned_org_unit_id` -> `org_unit`.`id`<br>`created_by_user_id` -> `application_users`.`id`<br>`network_device_id` -> `network_devices`.`id`<br>`updated_by_user_id` -> `application_users`.`id`<br>`vehicle_id` -> `vehicle`.`id` | `dotazioni_custodies`.`asset_id` -> `id`<br>`dotazioni_events`.`asset_id` -> `id` |
| `dotazioni_custodies` | Contiene dati relativi a dotazioni custodies. | id | taken_at, returned_at, notes, return_notes | `asset_id` -> `dotazioni_assets`.`id`<br>`handover_from_user_id` -> `application_users`.`id`<br>`holder_user_id` -> `application_users`.`id`<br>`recorded_by_user_id` -> `application_users`.`id`<br>`returned_by_user_id` -> `application_users`.`id` | - |
| `dotazioni_events` | Contiene dati relativi a dotazioni eventi. | id | action, details | `actor_user_id` -> `application_users`.`id`<br>`asset_id` -> `dotazioni_assets`.`id` | - |
