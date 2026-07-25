<p align="center">
<img src="docs/immich2gpx_logo.png" width="50%">
<br>
<img src="docs/immich2gpx_text.svg" width="50%">
</p>

**immich2gpx** is a command-line tool that queries filtered media metadata from an **[Immich](https://immich.app/) server** and exports EXIF location data to **GPX files**.

⚠️ *immich2gpx* is an independent project and is not affiliated with, endorsed by, or officially supported by [Immich](https://immich.app/).

## ✨ Features

- Query the Immich API with flexible filters
- Modular YAML configuration with `!include` support
- Reusable filter references (`!ref`)
- Nested and composable jobs
- Supports complex logical filters with Boolean operators (`and` / `or`)
- Metadata analysis `--show`, `--group`, `--compare-with`
- GPX export with track segmentation based on query logic
- Simulation mode without requiring an Immich server `--simulate`
- Fully typed, mypy-clean Python codebase

## 🚀 Getting Started in 3 Steps

Get started with *immich2gpx* in minutes.
Detailed guides are linked below.

### 1️⃣ Install *immich2gpx*

Clone the repository and install dependencies:

```bash
git clone https://github.com/Griffsano/immich2gpx.git
cd immich2gpx
pip install --upgrade -r requirements.txt
```

You can also use `make` and/or create a virtual Python environment, have a look at the alternative installation options in the [Installation Guide](docs/installation.md).

### 2️⃣ Configure the Tool

Copy the [quickstart example configuration](config/example_quickstart.yaml):

```bash
cp config/example_quickstart.yaml immich2gpx.yaml
```

- Set your Immich server URL
- Add your API key, see [Immich API Key Setup](docs/immich_api_key.md)

### 3️⃣ Run Your First Job

```bash
immich2gpx --job recents --gpx --show
```

This will query your Immich server and export a GPX track based on recent photos.

You can start by learning [how to run jobs and analyze data](docs/usage.md), then explore [examples of modular YAML configuration](docs/config_composition.md).
Finally, refer to the [full configuration schema](docs/config_schema.md) for a complete overview of all available options.

## 📚 Documentation

- **[Installation Guide](docs/installation.md)** – Instructions for installing *immich2gpx*, including environment setup and optional developer dependencies.
- **[Immich API Key Setup](docs/immich_api_key.md)** – Steps to create a read-only Immich API key and configure it for use with *immich2gpx*.
- **[Usage Overview](docs/usage.md)** – Reference for running the CLI tool, including available options and common command workflows.
- **[Configuration Composition](docs/config_composition.md)** – Guide to structuring modular configurations using includes and reusable references.
- **[Configuration Schema](docs/config_schema.md)** – Complete reference of all configuration sections, fields, and supported values.

## 📝 License

*immich2gpx* is licensed under the **GNU Affero General Public License v3** (GNU AGPLv3).
See the [LICENSE file](LICENSE) for details.

## 🤖 Note on AI Assistance

This software was developed with the assistance of **ChatGPT (OpenAI)**.
AI assistance was used for code generation, design review, documentation, and graphical asset generation.
