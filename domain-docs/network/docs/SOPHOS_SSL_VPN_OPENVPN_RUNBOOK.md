# GAIA Rete - Runbook accesso remoto con Sophos SSL VPN e OpenVPN

## Scopo

Questo runbook descrive come configurare Sophos Firewall per consentire l'accesso
a GAIA da fuori sede tramite VPN OpenVPN, mantenendo lo stesso URL usato in sede:

```text
http://gaia.lan
```

L'obiettivo operativo e avere:

- accesso locale completo dalla LAN aziendale
- accesso remoto tramite VPN per Windows e Android
- nessuna esposizione pubblica diretta di GAIA su Internet
- un solo endpoint applicativo, `gaia.lan`, valido sia in LAN sia in VPN
- tracciamento GAIA degli accessi per utente e dispositivo applicativo
- blocco operativo quando un utente supera i dispositivi autorizzati

## Architettura target

```text
Utente in sede
  -> DNS interno/Sophos: gaia.lan -> 192.168.1.110
  -> Server CED
  -> nginx host
  -> stack GAIA Docker

Utente fuori sede
  -> OpenVPN / Sophos SSL VPN
  -> DNS interno/Sophos: gaia.lan -> 192.168.1.110
  -> Server CED
  -> nginx host
  -> stack GAIA Docker
```

## Assunzioni operative

- Firewall: Sophos Firewall / Sophos XGS.
- Server GAIA CED: `192.168.1.110`.
- Dominio interno GAIA: `gaia.lan`.
- Client previsti: Windows e Android.
- Client VPN: OpenVPN Connect, oppure Sophos Connect su Windows se gia adottato.
- Modalita consigliata: SSL VPN con split tunnel.
- Utenti VPN Sophos e utenti applicativi GAIA coincidono per `username`.
- Ogni utente VPN usa una chiave/profilo personale utente, non un profilo condiviso.
- GAIA applica il limite iniziale di `4` dispositivi applicativi attivi per utente.

Se l'IP del server CED cambia, aggiornare tutti i riferimenti a
`192.168.1.110`.

## Policy accessi e dispositivi GAIA

### Regola operativa iniziale

Ogni utente puo avere al massimo:

```text
4 dispositivi GAIA attivi
```

Il limite e applicato sui dispositivi registrati da GAIA al login, non sulle
sole connessioni contemporanee Sophos. Questo evita una policy troppo
stringente e consente all'utente di usare normalmente PC ufficio, portatile,
telefono e un eventuale secondo browser/dispositivo.

Quando viene superato il limite:

- GAIA non emette il token applicativo;
- il login viene negato con messaggio operativo;
- viene registrata una sessione `login_blocked`;
- un amministratore deve disattivare, bloccare o revocare un dispositivo
  precedente prima che il nuovo device possa accedere.

### Chiave privata utente

Per il primo rilascio il profilo VPN resta personale per utente:

```text
1 utente Sophos = 1 profilo/chiave VPN personale
```

Questa scelta e compatibile con l'avvio operativo, ma ha un limite importante:
se il profilo viene copiato su piu dispositivi, Sophos identifica l'utente ma
non distingue in modo forte il singolo dispositivo. Per questo GAIA registra un
identificativo dispositivo applicativo generato nel browser e lo usa per il
limite dei `4` device.

Evoluzione consigliata: passare a certificati/profili per dispositivo associati
allo stesso utente, cosi ogni revoca puo colpire un solo device senza ruotare
l'intero profilo utente.

### Tracciamento GAIA

GAIA registra:

- `network_vpn_devices`: dispositivi applicativi autorizzati o revocati per
  utente;
- `network_vpn_sessions`: sessioni e tentativi di login consentiti/bloccati;
- username GAIA/Sophos, fingerprint dispositivo, user-agent, IP visto da GAIA,
  timestamp e motivo del blocco.

Endpoint amministrativi disponibili:

```text
GET /api/network/vpn-access/devices
GET /api/network/vpn-access/sessions
PATCH /api/network/vpn-access/devices/{device_id}
```

UI amministrativa:

```text
Rete -> Accessi VPN
/network/vpn-access
```

La pagina mostra KPI, dispositivi attivi/bloccati/revocati, sessioni
`login_allowed`/`login_blocked` e consente ad admin/super admin di attivare,
bloccare o revocare un dispositivo.

Stati dispositivo:

- `active`: dispositivo autorizzato e conteggiato nel limite;
- `blocked`: dispositivo bloccato temporaneamente;
- `revoked`: dispositivo revocato, richiede nuova autorizzazione operativa.

Variabili GAIA:

```env
NETWORK_VPN_DEVICE_ENFORCEMENT_ENABLED=true
NETWORK_VPN_MAX_ACTIVE_DEVICES_PER_USER=4
```

Se serve una fase di osservazione senza blocco, impostare temporaneamente:

```env
NETWORK_VPN_DEVICE_ENFORCEMENT_ENABLED=false
```

In produzione la raccomandazione resta `true`.

## Scelta del perimetro VPN

### Opzione consigliata per il primo rilascio

Limitare la VPN al solo server GAIA:

```text
192.168.1.110/32
```

Vantaggi:

- superficie di accesso minima
- regole firewall piu semplici
- rischio operativo ridotto

### Opzione accesso LAN completo

Consentire l'accesso alla subnet LAN:

```text
192.168.1.0/24
```

Usare questa opzione solo se gli utenti remoti devono raggiungere anche altri
servizi interni oltre GAIA. In questo caso evitare regole `Any -> Any` e
definire regole per servizi/destinazioni necessari.

## Parametri consigliati

```text
VPN type: SSL VPN remote access
VPN pool: 10.250.10.0/24
Local network, opzione minima: 192.168.1.110/32
Local network, opzione LAN: 192.168.1.0/24
DNS server distribuito ai client: Sophos o DNS interno
Record DNS: gaia.lan -> 192.168.1.110
Servizi consentiti verso GAIA: HTTP, HTTPS
```

## Configurazione Sophos

### 1. Creare il gruppo utenti VPN

Creare un gruppo dedicato, ad esempio:

```text
GAIA-VPN-Users
```

Associare al gruppo solo gli utenti autorizzati ad accedere a GAIA da remoto.
Se disponibile, abilitare MFA per gli utenti VPN.

### 2. Configurare il pool SSL VPN

Nel firewall Sophos configurare un pool IP dedicato ai client VPN:

```text
10.250.10.0/24
```

Il pool deve essere diverso dalla LAN aziendale e non deve sovrapporsi alle
reti domestiche piu comuni se possibile.

### 3. Configurare SSL VPN remote access

Nel profilo SSL VPN:

- abilitare il gruppo `GAIA-VPN-Users`
- assegnare il pool VPN `10.250.10.0/24`
- impostare come risorse raggiungibili una delle seguenti reti:
  - solo GAIA: `192.168.1.110/32`
  - LAN completa: `192.168.1.0/24`
- usare split tunnel, salvo esigenze diverse esplicite
- distribuire ai client VPN il DNS interno/Sophos

Per il caso GAIA, lo split tunnel e preferibile: sulla VPN passa solo il
traffico verso la rete interna, mentre la navigazione Internet dell'utente resta
sulla connessione locale.

### 4. Configurare DNS per LAN e VPN

Il nome deve risolvere nello stesso modo sia in sede sia da VPN:

```text
gaia.lan -> 192.168.1.110
```

Verificare che il DNS assegnato ai client VPN sia in grado di risolvere
`gaia.lan`. Se Sophos gestisce il DNS interno, creare o verificare la voce host
su Sophos.

### 5. Creare le regole firewall

Regola minima per GAIA:

```text
Source zone: VPN
Source network/user: SSL VPN pool oppure GAIA-VPN-Users
Destination zone: LAN
Destination network: 192.168.1.110
Services: HTTP, HTTPS
Action: Allow
Log traffic: Enabled
```

Se si usa l'opzione LAN completa, creare regole aggiuntive solo per i servizi
realmente necessari. Non usare una regola generica `VPN -> LAN -> Any` se non
come test temporaneo e tracciato.

### 6. Evitare esposizione pubblica

Non creare NAT o port forwarding WAN verso GAIA.

GAIA deve essere raggiungibile da:

- LAN interna
- pool VPN autorizzato

GAIA non deve essere raggiungibile direttamente da Internet.

## Distribuzione profilo ai client

### Windows

Opzioni supportate:

- OpenVPN Connect con profilo `.ovpn`
- Sophos Connect, se lo standard operativo CED lo prevede

Procedura:

1. Installare il client scelto.
2. Scaricare il profilo VPN dal portale utente Sophos.
3. Importare il profilo.
4. Connettersi con le credenziali personali.
5. Aprire `http://gaia.lan`.

### Android

Usare OpenVPN Connect.

Procedura:

1. Installare OpenVPN Connect.
2. Scaricare o ricevere il profilo `.ovpn`.
3. Importare il profilo nell'app.
4. Connettersi con le credenziali personali.
5. Aprire `http://gaia.lan` dal browser.

## Verifiche lato client

Con VPN attiva, da Windows:

```powershell
nslookup gaia.lan
ping 192.168.1.110
curl http://gaia.lan/api/health
```

Risultati attesi:

- `nslookup gaia.lan` restituisce `192.168.1.110`
- il server `192.168.1.110` risponde, se ICMP non e bloccato
- `http://gaia.lan/api/health` restituisce una risposta HTTP valida
- `http://gaia.lan` apre la login di GAIA

Su Android:

- verificare che OpenVPN Connect risulti connesso
- aprire `http://gaia.lan`
- se il nome non risolve, provare temporaneamente `http://192.168.1.110`
  per distinguere problema DNS da problema routing/firewall

## Verifiche lato server GAIA

Sul server CED:

```bash
curl http://127.0.0.1:8080/api/health
curl -H "Host: gaia.lan" http://127.0.0.1/api/health
```

Risultati attesi:

- lo stack Docker risponde sulla porta interna `8080`
- nginx host inoltra correttamente il virtual host `gaia.lan`

## Configurazione GAIA attesa

Nel file `.env.production` del deploy CED mantenere:

```env
FRONTEND_PUBLIC_URL=http://gaia.lan
NEXT_PUBLIC_API_BASE_URL=/api
BACKEND_CORS_ORIGINS=http://gaia.lan,https://gaia.lan
NGINX_PORT=8080
```

Il deploy standard normalizza `NEXT_PUBLIC_API_BASE_URL=/api` e aggiorna le
origini CORS per il dominio configurato:

```bash
GAIA_DOMAIN=gaia.lan CONFIGURE_HOST_NGINX=yes ./scripts/deploy-ced-gaia.sh
```

## Troubleshooting

### `gaia.lan` non risolve da VPN

Cause probabili:

- DNS interno non distribuito ai client VPN
- record `gaia.lan` mancante sul DNS/Sophos
- client che continua a usare DNS pubblici

Verifiche:

```powershell
nslookup gaia.lan
ipconfig /all
```

### `gaia.lan` risolve ma la pagina non apre

Cause probabili:

- rotta VPN verso `192.168.1.110/32` o `192.168.1.0/24` mancante
- regola firewall VPN -> LAN assente o troppo restrittiva
- nginx host non attivo sul server CED
- stack GAIA non attivo

Verifiche:

```powershell
ping 192.168.1.110
curl http://192.168.1.110/api/health
curl http://gaia.lan/api/health
```

### Funziona da Windows ma non da Android

Cause probabili:

- profilo `.ovpn` non compatibile con la versione del client
- DNS non applicato sul client Android
- Android usa DNS privato/DoH configurato manualmente

Verifiche:

- disabilitare temporaneamente DNS privato Android
- reimportare il profilo OpenVPN
- testare `http://192.168.1.110`

### Funziona via IP ma non via nome

Il routing VPN e la regola firewall sono corretti; il problema e DNS.
Correggere la distribuzione DNS della SSL VPN o la voce `gaia.lan`.

## Criteri di accettazione

La configurazione e pronta quando:

1. un client Windows fuori sede si connette via OpenVPN e apre `http://gaia.lan`
2. un client Android fuori sede si connette via OpenVPN e apre `http://gaia.lan`
3. `gaia.lan` risolve `192.168.1.110` sia in LAN sia in VPN
4. GAIA non e raggiungibile da Internet senza VPN
5. Sophos registra traffico VPN verso `192.168.1.110`
6. gli utenti non autorizzati non possono autenticarsi o ricevere profili VPN
7. GAIA registra i login in `network_vpn_sessions`
8. GAIA espone i dispositivi in `network_vpn_devices` via API amministrative
9. il quinto dispositivo attivo dello stesso utente viene bloccato da GAIA

## Riferimenti

- Sophos Firewall - SSL VPN remote access:
  https://docs.sophos.com/nsg/sophos-firewall/20.0/Help/en-us/webhelp/onlinehelp/VPNAndUserPortalHelp/VPN/RemoteAccessVPN/SSLVPNRemoteAccess/
- Sophos KB - OpenVPN Connect su Android:
  https://support.sophos.com/support/s/article/KBA-000006807
