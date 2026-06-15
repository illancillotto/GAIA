[Unit]
Description=GAIA -> Gate Mobile Gateway sync
Wants=network-online.target docker.service
After=network-online.target docker.service

[Service]
Type=oneshot
WorkingDirectory={{CED_PROJECT_DIR}}
ExecStart={{DOCKER_BIN}} compose --env-file {{ENV_FILE}} exec -T backend python -m app.scripts.gate_mobile_sync
TimeoutStartSec=120

