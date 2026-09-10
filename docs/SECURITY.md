# Security Policy

## Supported Versions

Use this section to tell people about which versions of your project are
currently being supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| 5.1.x   | :white_check_mark: |
| 5.0.x   | :x:                |
| 4.0.x   | :white_check_mark: |
| < 4.0   | :x:                |

## Reporting a Vulnerability

Use this section to tell people how to report a vulnerability.

Tell them where to go, how often they can expect to get an update on a
reported vulnerability, what to expect if the vulnerability is accepted or
declined, etc.

## Frontend GIS

- Il runtime cartografico supportato e `maplibre-gl@6.9.0`, successivo al range
  vulnerabile `<=6.4.0` di GHSA-jrc7-96c5-q579.
- Il lockfile non deve contenere copie di MapLibre 4.x o `kt-maplibre-gl`.
  `maplibre-gl-draw` e stato sostituito da `terra-draw` con adapter MapLibre.
- I popup Catasto continuano a usare contenuto HTML costruito localmente:
  ogni valore interpolato viene escapato e i parametri degli URL vengono
  codificati prima di raggiungere `Popup.setHTML`.
- Le sorgenti tile e style operative sono governate da GAIA, Martin e QGIS
  Server. L'introduzione di sorgenti o markup non fidati richiede una nuova
  threat analysis del confine MapLibre.
- MapLibre 6 richiede WebGL2. L'assenza del contesto produce un errore esplicito
  nelle mappe Catasto, catalogo e tracce GPS, senza fallback a WebGL1.
