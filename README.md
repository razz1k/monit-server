# Server (central monitoring)

This directory contains the central monitoring stack.

## Components

- `Prometheus` (metrics collection and storage)
- `Alertmanager` (alert routing)
- `Grafana` (dashboards and UI)
- `Loki` (central logs storage)
- `blackbox_exporter` (HTTP/TCP/ICMP probes)
- VPS agents: `node_exporter` and `systemd_exporter` behind nginx on port `9443` (deployed from the `client` stack)

## Files

- `docker-compose.yml` - central services
- `prometheus/prometheus.yml` - scrape and alerting config
- `prometheus/targets/node_vps.json` - file_sd targets for `node_exporter` on VPS hosts
- `prometheus/targets/systemd_vps.json` - file_sd targets for `systemd_exporter` on VPS hosts
- `prometheus/alerts/node.yml` - base host alert rules
- `prometheus/alerts/systemd.yml` - systemd unit alert rules
- `alertmanager/alertmanager.yml.template` - Alertmanager config template (`TELEGRAM_*` from `.env`)
- `.env` - secrets (not committed); copy from `.env.example`
- `blackbox/blackbox.yml` - probe modules
- `loki/config.yml` - Loki single-node config
- `grafana/provisioning/datasources/datasources.yml` - datasource provisioning

## Quick start

1. Create `.env` from the example and set secrets (Compose reads `.env` from this directory automatically):
   - `cp .env.example .env`
   - `GF_SECURITY_ADMIN_USER`, `GF_SECURITY_ADMIN_PASSWORD` for Grafana
   - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` for Alertmanager (rendered from `alertmanager.yml.template` at container start)
   - copy `prometheus/targets/node_vps.json.example` to `prometheus/targets/node_vps.json` and set scrape targets to `host:9443` (nginx on each VPS)
   - copy `prometheus/targets/systemd_vps.json.example` to `prometheus/targets/systemd_vps.json` with the **same** `host:9443` list (paths differ via `metrics_path` in `prometheus.yml`)
2. Start stack:

```bash
docker compose up -d
```

3. Verify:
   - Grafana: `http://<monitoring-server>:3000`
   - Prometheus targets: `http://<monitoring-server>:9090/targets`
   - Alertmanager: `http://<monitoring-server>:9093`
4. Add/remove VPS by editing `prometheus/targets/node_vps.json` and `prometheus/targets/systemd_vps.json`, then wait up to 30s (or call Prometheus reload).

## file_sd notes

- The `node` scrape job reads only `prometheus/targets/node_vps.json` (mapped to `/etc/prometheus/targets/node_vps.json` in the container).
- The `systemd` scrape job reads only `prometheus/targets/systemd_vps.json`.
- Keep the same host list in both files, using port `9443` on each VPS. The `node` job scrapes `/metrics/node`, the `systemd` job scrapes `/metrics/systemd` (see `prometheus/prometheus.yml`).
- Example JSON structure:

```json
[
  {
    "labels": { "job": "node", "env": "prod" },
    "targets": ["10.10.10.11:9443"]
  }
]
```

## Recommended network policy

- Allow `9443/tcp` on VPS only from this server (or VPN subnet)
- Allow `3100/tcp` on this server only from VPS/VPN subnet
- Do not expose `9090`, `9093`, `9115` publicly without access control
