# Home Assistant Custom Integration Development Container
# Python 3.13 required for Home Assistant as of Nov 2025
# Reference: https://developers.home-assistant.io/docs/development_environment/

FROM mcr.microsoft.com/devcontainers/python:3.14

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SHELL=/usr/bin/zsh

# Install system dependencies required by Home Assistant and media processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build essentials
    build-essential \
    cmake \
    autoconf \
    # Media processing (required for media_player components)
    ffmpeg \
    libturbojpeg0 \
    libturbojpeg0-dev \
    # Network capture (useful for debugging)
    libpcap-dev \
    # Bluetooth support
    libbluetooth-dev \
    # Additional tools
    curl \
    wget \
    jq \
    # Shell enhancements
    zsh \
    fzf \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create Home Assistant configuration directory
RUN mkdir -p /workspaces/config/custom_components

# Switch to vscode user for remaining setup
USER vscode

# Create virtual environment for Home Assistant development
ENV HA_VENV=/home/vscode/.local/ha-venv
RUN python -m venv ${HA_VENV}

# Install Home Assistant and development dependencies in venv
RUN ${HA_VENV}/bin/pip install --upgrade pip setuptools wheel && \
    ${HA_VENV}/bin/pip install \
    homeassistant \
    pytest \
    pytest-asyncio \
    pytest-cov \
    pytest-homeassistant-custom-component \
    ruff \
    mypy \
    pre-commit

# Set up Oh My Zsh for better terminal experience
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended || true

# Add useful aliases and PATH configuration
RUN echo '\n# Home Assistant Development\n\
export PATH="${HA_VENV}/bin:$PATH"\n\
alias ha="hass -c /workspaces/config"\n\
alias halog="tail -f /workspaces/config/home-assistant.log"\n\
alias pytest="python -m pytest"\n\
alias ruff-check="ruff check ."\n\
alias ruff-fix="ruff check --fix ."\n\
\n# uv configuration\n\
export UV_LINK_MODE=copy\n\
' >> /home/vscode/.zshrc

# Add to bashrc as fallback
RUN echo '\n# Home Assistant Development\n\
export PATH="${HA_VENV}/bin:$PATH"\n\
alias ha="hass -c /workspaces/config"\n\
alias halog="tail -f /workspaces/config/home-assistant.log"\n\
alias pytest="python -m pytest"\n\
export UV_LINK_MODE=copy\n\
' >> /home/vscode/.bashrc

# Set working directory
WORKDIR /workspaces

# Default command
CMD ["sleep", "infinity"]
