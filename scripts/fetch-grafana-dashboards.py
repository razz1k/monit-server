#!/usr/bin/env python3
"""Download community dashboards from grafana.com and rewrite datasource refs to provisioned UIDs."""

import json
import os
import sys
import urllib.request

PROM_UID = "prometheus"
LOKI_UID = "loki"

DASHBOARDS = [
    (1860, "node-exporter-full.json", True),
    (22872, "systemd-exporter.json", True),
    (7587, "blackbox-exporter.json", True),
    (3662, "prometheus-overview.json", True),
    (24978, "log-dashboard-with-filtering.json", False),
]


def fix_ds(obj, prom_only: bool):
    if isinstance(obj, dict):
        if "datasource" in obj:
            ds = obj["datasource"]
            if isinstance(ds, str) and ds.startswith("${"):
                if prom_only:
                    obj["datasource"] = {"type": "prometheus", "uid": PROM_UID}
                else:
                    obj["datasource"] = {"type": "loki", "uid": LOKI_UID}
            elif isinstance(ds, dict):
                u = ds.get("uid")
                if isinstance(u, str) and u.startswith("${"):
                    t = ds.get("type", "prometheus")
                    obj["datasource"]["uid"] = PROM_UID if t == "prometheus" else LOKI_UID
        if obj.get("uid") == "${ds_prometheus}":
            obj["uid"] = PROM_UID
        for v in obj.values():
            fix_ds(v, prom_only)
    elif isinstance(obj, list):
        for item in obj:
            fix_ds(item, prom_only)


def fix_templating_prometheus(d):
    t = d.get("templating")
    if not t or "list" not in t:
        return
    for x in t["list"]:
        if x.get("name") == "ds_prometheus" and x.get("type") == "datasource":
            x["current"] = {
                "selected": True,
                "text": "Prometheus",
                "value": PROM_UID,
            }
        if x.get("type") == "datasource" and x.get("query") == "prometheus":
            x["current"] = {
                "selected": True,
                "text": "Prometheus",
                "value": PROM_UID,
            }
        ds = x.get("datasource")
        if isinstance(ds, dict) and isinstance(ds.get("uid"), str) and ds["uid"].startswith("${"):
            ds["uid"] = PROM_UID


def fix_templating_loki(d):
    t = d.get("templating")
    if not t or "list" not in t:
        return
    for x in t["list"]:
        if x.get("type") == "datasource" and x.get("query") == "loki":
            x["current"] = {
                "selected": True,
                "text": "Loki",
                "value": LOKI_UID,
            }
        # Dashboard 24978: "All" for filename must expand to a regex that matches every path.
        if x.get("name") == "filename" and x.get("type") == "query" and x.get("includeAll"):
            x["allValue"] = ".+"


def fix_log_dashboard_avg_throughput_panel(d):
    """Grafana 11+: Stat fieldConfig color mode 'background' is invalid; use thresholds. Loki rate[5m] instant."""
    for panel in d.get("panels", []):
        if panel.get("title") != "Avg Throughput":
            continue
        for tgt in panel.get("targets") or []:
            if tgt.get("refId") == "A":
                tgt["expr"] = (
                    'sum(rate({job="varlogs", filename=~"$filename"}[5m])) or vector(0)'
                )
                tgt["editorMode"] = "code"
                tgt["queryType"] = "instant"
        panel["fieldConfig"] = {
            "defaults": {
                "unit": "pps",
                "color": {
                    "mode": "thresholds",
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [{"color": "green", "value": None}],
                    },
                },
            },
            "overrides": [],
        }
        panel["options"] = {
            "colorMode": "value",
            "graphMode": "none",
            "justifyMode": "auto",
            "orientation": "auto",
            "reduceOptions": {
                "calcs": ["lastNotNull"],
                "fields": "",
                "values": False,
            },
            "textMode": "auto",
        }
        break


def ensure_loki_panels_have_datasource(d):
    """Grafana uses the org default datasource when panel.datasource is missing; set Loki on each panel."""
    for panel in d.get("panels", []):
        if panel.get("type") == "row":
            continue
        targets = panel.get("targets") or []
        if not targets:
            continue
        ds0 = targets[0].get("datasource") or {}
        if ds0.get("type") == "loki" or ds0.get("uid") == LOKI_UID:
            panel["datasource"] = {"type": "loki", "uid": LOKI_UID}


def fetch_and_prepare(dash_id: int, prom_only: bool) -> dict:
    url = f"https://grafana.com/api/dashboards/{dash_id}/revisions/latest/download"
    with urllib.request.urlopen(url, timeout=60) as resp:
        payload = json.load(resp)
    d = payload.get("dashboard", payload)
    d.pop("__inputs", None)
    d.pop("__elements", None)
    d.pop("__requires", None)
    d.pop("version", None)
    d["id"] = None
    fix_ds(d, prom_only)
    if prom_only:
        fix_templating_prometheus(d)
    else:
        fix_templating_loki(d)
        ensure_loki_panels_have_datasource(d)
        if dash_id == 24978:
            fix_log_dashboard_avg_throughput_panel(d)
            d["refresh"] = "30s"
    return d


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    outdir = os.path.join(root, "grafana", "dashboards")
    os.makedirs(outdir, exist_ok=True)
    for dash_id, filename, prom_only in DASHBOARDS:
        print(f"fetch {dash_id} -> {filename}")
        d = fetch_and_prepare(dash_id, prom_only)
        path = os.path.join(outdir, filename)
        with open(path, "w") as f:
            json.dump(d, f, indent=2)
            f.write("\n")
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
