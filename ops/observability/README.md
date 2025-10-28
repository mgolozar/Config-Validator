# Config Validator - Observability Stack

This directory contains a complete Grafana/Loki/Promtail observability stack for monitoring config validator reports.

## Quick Start

1. Start the stack:
   ```bash
   docker-compose up -d
   ```

2. Access Grafana:
   - URL: http://localhost:3000
   - Username: `admin`
   - Password: `admin`

3. Logs are automatically provisioned:
   - Loki runs on port 3100
   - Promtail collects from `../../reports/*.ndjson`
   - Dashboards are auto-loaded from `grafana/dashboards/`

## Architecture

```
┌─────────────────┐
│   Promtail      │ ← reads ../../reports/*.ndjson
│  (Log Shipper)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│      Loki       │ ← storage (port 3100)
│ (Log Aggregator)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Grafana      │ ← visualization (port 3000)
│  (Dashboards)   │
└─────────────────┘
```

## Directory Structure

```
ops/observability/
├── docker-compose.yml                          # Main orchestration
├── promtail-config.yml                         # Promtail scrape config
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/datasource.yml          # Loki data source
│   │   └── dashboards/dashboards.yml           # Dashboard provisioning
│   └── dashboards/Config Validator/
│       ├── 01-overview.json                    # Overview dashboard
│       └── 02-errors-and-trends.json           # Error analysis
└── README.md                                    # This file
```

## Using the Stack

### Prerequisites
- Reports must be in NDJSON format in `../../reports/*.ndjson`
- Use `tools/report_to_ndjson.py` to convert JSON reports to NDJSON

### Common Operations

**View logs in Grafana:**
- Go to Explore
- Select "Loki" data source
- Query: `{job="config-validator"}`

**Custom dashboards:**
- Edit JSON files in `grafana/dashboards/Config Validator/`
- Restart: `docker-compose restart grafana`

**Export/Share this stack:**
- Copy the entire `ops/observability/` directory
- Volume paths are relative to this directory

## Useful Queries

**All summary records:**
```
{job="config-validator", type="summary"}
```

**Invalid files only:**
```
{job="config-validator", type="file"} | json | valid="false"
```

**Error count by run:**
```
sum by (run_id) ({job="config-validator", type="file"} | json | error_count)
```

**Files by registry:**
```
count by (registry) ({job="config-validator", type="file"} | json | registry!="")
```

## Troubleshooting

**Check logs:**
```bash
docker-compose logs promtail
docker-compose logs loki
docker-compose logs grafana
```

**Reset everything:**
```bash
docker-compose down -v
docker-compose up -d
```

**Verify Promtail is reading files:**
```bash
docker-compose exec promtail cat /var/log/reports/stream.ndjson | head
```

