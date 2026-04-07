# Server (central monitoring)

This directory contains the central monitoring stack.

## Components

- `Prometheus` (metrics collection and storage)
- `Alertmanager` (alert routing)
- `Grafana` (dashboards and UI)
- `Loki` (central logs storage)
- `blackbox_exporter` (HTTP/TCP/ICMP probes)

## Files

- `docker-compose.yml` - central services
- `prometheus/prometheus.yml` - scrape and alerting config
- `prometheus/targets/node_vps.json` - file_sd targets for VPS nodes
- `prometheus/alerts/node.yml` - base alert rules
- `alertmanager/alertmanager.yml` - receivers and routes
- `blackbox/blackbox.yml` - probe modules
- `loki/config.yml` - Loki single-node config
- `grafana/provisioning/datasources/datasources.yml` - datasource provisioning

## Quick start

1. Update secrets/placeholders:
   - `GF_SECURITY_ADMIN_PASSWORD` in `docker-compose.yml`
   - Telegram token/chat in `alertmanager/alertmanager.yml` (if used)
   - node targets in `prometheus/targets/node_vps.json`
2. Start stack:

```bash
docker compose up -d
```

3. Verify:
   - Grafana: `http://<monitoring-server>:3000`
   - Prometheus targets: `http://<monitoring-server>:9090/targets`
   - Alertmanager: `http://<monitoring-server>:9093`
4. Add/remove VPS by editing `prometheus/targets/node_vps.json`, then wait up to 30s (or call Prometheus reload).

## file_sd notes

- Prometheus reads VPS targets from `/etc/prometheus/targets/*.json`.
- In this repository, that path is backed by `./prometheus/targets`.
- Example JSON structure:

```json
[
  {
    "labels": { "job": "node", "env": "prod" },
    "targets": ["10.10.10.11:9100"]
  }
]
```

## Recommended network policy

- Allow `9100/tcp` on VPS only from this server (or VPN subnet)
- Allow `3100/tcp` on this server only from VPS/VPN subnet
- Do not expose `9090`, `9093`, `9115` publicly without access control
