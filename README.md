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
- `grafana/provisioning/datasources/datasources.yml` - datasource provisioning (stable `uid`: `prometheus`, `loki`)
- `grafana/provisioning/dashboards/dashboards.yml` - file-based dashboards
- `grafana/dashboards/*.json` - bundled community dashboards (see below)

## Quick start

1. Create `.env` from the example and set secrets (Compose reads `.env` from this directory automatically):
   - `cp .env.example .env`
   - `GF_SECURITY_ADMIN_USER`, `GF_SECURITY_ADMIN_PASSWORD` for Grafana
   - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` for Alertmanager (rendered from `alertmanager.yml.template` at container start)
   - copy `prometheus/targets/node_vps.json.example` to `prometheus/targets/node_vps.json` and set scrape targets to `host:9443` (nginx on each VPS)
   - copy `prometheus/targets/systemd_vps.json.example` to `prometheus/targets/systemd_vps.json` with the **same** hosts and the **same** `hostname` label per host as in `node_vps.json` (paths differ via `metrics_path` in `prometheus.yml`)
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
- Optional label **`hostname`** (same value for the same machine in **both** JSON files) is used in Telegram for `InstanceDown`: readable host line and `Targets [node, systemd, …]` in one message. If omitted, the template strips the trailing `:port` from `instance` for the `host:` line and still shows full `endpoint:`.
- Example JSON structure (one object per host):

```json
[
  {
    "targets": ["10.10.10.11:9443"],
    "labels": { "env": "prod", "hostname": "vps-web-01" }
  }
]
```

## Telegram / Alertmanager

- Groups use `group_by: [alertname, instance]`. For **`InstanceDown`**, all scrape jobs that share the same `instance` (e.g. `node` and `systemd` on `:9443`) are merged into **one** Telegram message listing jobs in `Targets […]`.
- **`SystemdExporterDown`** was removed; unreachable `systemd` scrapes are covered by `InstanceDown` together with `node`.

## Bundled Grafana dashboards

Provisioned on startup (folder **Monitoring**):

| File | Grafana.com ID | Use |
|------|----------------|-----|
| `node-exporter-full.json` | [1860](https://grafana.com/grafana/dashboards/1860) | Node Exporter host metrics |
| `systemd-exporter.json` | [22872](https://grafana.com/grafana/dashboards/22872-systemd-exporter/) | systemd_exporter metrics |
| `blackbox-exporter.json` | [7587](https://grafana.com/grafana/dashboards/7587) | Blackbox probe metrics |
| `prometheus-overview.json` | [3662](https://grafana.com/grafana/dashboards/3662) | Prometheus server health |
| `log-dashboard-with-filtering.json` | [24978](https://grafana.com/grafana/dashboards/24978-log-dashboard-with-filtering/) | Loki + Promtail Linux logs (`job=varlogs`) |

JSON was post-processed to point datasources at provisioned UIDs `prometheus` and `loki`. To refresh from grafana.com after changing datasource UIDs, run `python3 scripts/fetch-grafana-dashboards.py` from the `server` directory.

## Recommended network policy

- Allow `9443/tcp` on VPS only from this server (or VPN subnet)
- Allow `3100/tcp` on this server only from VPS/VPN subnet
- Do not expose `9090`, `9093`, `9115` publicly without access control
