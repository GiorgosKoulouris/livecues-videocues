#!/bin/bash
set -e

echo "Initializing development environment..."

############################
# Permissions
############################
sudo chown -R vscode:vscode /workspace/.venv
sudo chown -R vscode:vscode /home/vscode/.cache