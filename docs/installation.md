# 💻 Installation Guide

This guide explains how to set up the Python environment and install dependencies for *immich2gpx*.
You can use `make` to automate the process, manually configure a virtual environment, or manually install *immich2gpx* without virtual environment.

## 📝 Preparation

Clone the repository:
```bash
git clone https://github.com/Griffsano/immich2gpx.git
cd immich2gpx
```

## ⚙️ Installation Options

1. **Using `make`**

    - **With virtual environment (recommended)**
        ```bash
        make create-venv # Create virtual environment and upgrade pip
        make install     # Install runtime dependencies
        ```

   - **Without virtual environment**
        ```bash
        make install     # Install runtime dependencies
        ```

2. **Without `make`**

   - **With virtual environment (recommended)**
        ```bash
        python -m venv .venv                       # Create virtual environment
        # Activate the virtual environment:
        # source .venv/bin/activate                # for Linux/macOS
        # .venv\Scripts\activate                   # for Windows
        pip install --upgrade pip                  # Upgrade pip
        pip install --upgrade -r requirements.txt  # Install runtime dependencies
        ```

   - **Without virtual environment**

        ```bash
        pip install --upgrade -r requirements.txt      # Install runtime dependencies
        ```

## 👨‍💻 For Developers

This repository includes preconfigured tasks and settings for *Visual Studio Code*.

### Installing Development Dependencies

Install development dependencies (format/lint/test tools) with one of the following options:

- **Using `make`**
   ```bash
   make install-dev
   ```

   `make install-dev` already includes `make-install`.

- **With virtual environment**
   ```bash
   # Activate the virtual environment:
   # source .venv/bin/activate          # for Linux/macOS
   # .venv\Scripts\activate             # for Windows
   pip install -r requirements-dev.txt
   ```

- **Without virtual environment**
   ```bash
   pip install -r requirements-dev.txt
   ```

### Using the Makefile

Look into the [Makefile](../Makefile) or run `make` for useful development tools.
