# api-pulse

> Minimal uptime monitor that periodically pings REST endpoints and logs latency trends to a local SQLite database.

---

## Installation

```bash
pip install -r requirements.txt
```

Or install directly:

```bash
pip install api-pulse
```

---

## Usage

Define your endpoints in a `config.yaml` file:

```yaml
interval: 60  # seconds between checks
endpoints:
  - name: GitHub API
    url: https://api.github.com
  - name: My Service
    url: https://myservice.example.com/health
```

Then run the monitor:

```bash
python -m apipulse --config config.yaml
```

Latency data is automatically stored in a local `pulse.db` SQLite database. Query results anytime:

```bash
python -m apipulse --report
```

Example output:

```
Endpoint          Status    Avg Latency    Last Checked
----------------  --------  -------------  -------------------
GitHub API        UP        142ms          2024-03-15 10:32:01
My Service        UP        89ms           2024-03-15 10:32:03
```

---

## Features

- Periodic health checks with configurable intervals
- Latency trend logging to SQLite (no external dependencies)
- Simple YAML-based configuration
- CLI report viewer

---

## Requirements

- Python 3.8+
- `requests`
- `pyyaml`

---

## License

This project is licensed under the [MIT License](LICENSE).