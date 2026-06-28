FROM mcr.microsoft.com/devcontainers/base:ubuntu

USER root

RUN apt-get update && \
    apt-get install -y \
        curl \
        git \
        python3 \
        python3-venv \
        python3-pip

USER vscode

RUN curl -fsSL https://claude.ai/install.sh | bash