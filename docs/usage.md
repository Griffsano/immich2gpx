# ⚡ Usage Overview

Run *immich2gpx* from CLI:

```bash
immich2gpx --config config.yaml
# or
python3 -m immich2gpx --job main --gpx
```

## 🛠️ CLI Options

| Option               | Argument                               | Description                                                         |
| -------------------- | -------------------------------------- | ------------------------------------------------------------------- |
| `-h`, `--help`       |                                        | Show a help message and exit.                                       |
| `--version`          |                                        | Show program version and exit.                                      |
| `--config`           | `CONFIG`                               | Path to the YAML config file. Defaults to `immich2gpx.yaml`.        |
| `--check-connection` |                                        | Check connection to the Immich server.                              |
| `--job`              | `JOB`                                  | Defines the job to be run. Also executes sub-jobs.                  |
| `--gpx`              |                                        | Write the parsed EXIF location data to GPX files.                   |
| `--show`             |                                        | Execute the queries and print the resulting metadata.               |
| `--group`            |                                        | Execute the queries, group the media files, and print the metadata. |
| `--compare-with`     | `COMPARE_WITH`                         | Compare a job with the job specified by `--job`.                    |
| `--simulate`         |                                        | Output the Immich requests for analysis but do not execute them.    |
| `--logging-level`    | `DEBUG` / `INFO` / `WARNING` / `ERROR` | Define the logging level (DEBUG, INFO, WARNING, ERROR).             |

## 🏃 Example Workflows

### Check Connection to Immich Server

```bash
immich2gpx --check-connection
```

### Load Specific Config and Simulate Queries with Debug Logging

```bash
immich2gpx --config config.yaml --simulate --logging-level DEBUG
```

### Group Metadata for Analysis

```bash
immich2gpx --job main --group
```

### Compare Resulting Media Files of Two Jobs

```bash
immich2gpx --job main --compare-with previous
```

### Export GPX and Show Metadata

```bash
immich2gpx --job main --gpx --show
```
