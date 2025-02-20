#!/bin/bash

# Загрузка переменных окружения Rust
source "$HOME/.cargo/env"

echo "Установка Nexus CLI..."
curl https://cli.nexus.xyz/ | sh 