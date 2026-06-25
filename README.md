# Roman Data Monitoring Tool (RDMT) Spire

> [!CAUTION]
> The code in this repository is under heavy development and not currently intended for widespread use.
>
> Monitor development is tracked in [development status and prioritization](https://github.com/spacetelescope/rdmt-spire/blob/main/MONITOR_DEVELOPMENT.md) 
>
> This is a best-effort tool. While open-source, this project is not currently accepting pull-request contributions from external sources. If you would like to request a specific monitor be considered for implementation, please create a "Monitor Request" from the [New Issue button](https://github.com/spacetelescope/rdmt-spire/issues)
>
> If you have additional questions, see the [Contributing Guide](CONTRIBUTING.md).


RDMT-SPIRE is the arm of the Roman Data Monitoring Tool (RDMT) responsible for monitoring the science processing pipeline data from the Roman Space Telescope.

The files in the monitor directory tree contain the application logic for each of the RDMT-Spire's (Spire) data monitors.

Each directory is specific to a single monitor. In `rdmt-spire` v0.1, these are the astrometric and 1/f noise monitors. Before the files are ready for use in the Amazon Web Services (AWS) cloud-based RDMT pipeline, they must be packaged into a single Docker image. Do this in a local terminal by navigating to the monitor's directory and then following these steps:

### Prerequisites

- Python 3.12 or newer
- pip (or another Python package installer)

### Install from source

1. Clone the repository and enter the project directory.
2. Create and activate either a `venv` or Conda environment.
3. Install the package: `pip install .` for a standard install or `pip install -e .` for development.

#### Option A: `venv`

```bash
git clone https://github.com/spacetelescope/rdmt-spire.git
cd rdmt-spire

python3.12 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -e .
```

#### Option B: Conda

```bash
git clone https://github.com/spacetelescope/rdmt-spire.git
cd rdmt-spire

conda create -n rdmt-spire python=3.12 -y
conda activate rdmt-spire

pip install --upgrade pip
pip install -e .
```

## Contributing

Contribution guidelines are documented in [CONTRIBUTING.md](CONTRIBUTING.md).
