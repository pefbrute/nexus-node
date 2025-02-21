#!/bin/bash

# Проверяем, установлен ли screen
if ! command -v screen &> /dev/null; then
    echo "Установка screen..."
    sudo apt-get update && sudo apt-get install -y screen
fi

# Создаем новую screen сессию с именем nexus-install
screen -dmS nexus-install bash -c '
    source "$HOME/.cargo/env"
    echo "Установка Nexus CLI..."
    curl https://cli.nexus.xyz/ | sh
    echo "Установка завершена."
'

echo "Процесс запущен в screen сессии 'nexus-install'"
echo "Чтобы подключиться к сессии, выполните: screen -r nexus-install"
echo "Для отключения от сессии нажмите: Ctrl+A, затем D" 