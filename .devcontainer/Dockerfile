FROM mcr.microsoft.com/devcontainers/base:ubuntu

ARG STRIPE_CLI_VERSION=1.43.2

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