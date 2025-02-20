#!/bin/bash

# Загрузка переменных окружения Rust
source "$HOME/.cargo/env"

echo "Установка Nexus CLI..."
# Автоматически отвечаем Y на запрос подтверждения
yes Y | curl https://cli.nexus.xyz/ | sh 