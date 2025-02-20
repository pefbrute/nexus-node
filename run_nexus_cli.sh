#!/bin/bash

# Загрузка переменных окружения Rust
source "$HOME/.cargo/env"

echo "Установка Nexus CLI..."
printf 'Y\n' | curl https://cli.nexus.xyz/ | sh 