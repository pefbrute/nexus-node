#!/bin/bash

# Проверка root прав
if [ "$EUID" -ne 0 ]; then 
    echo "Этот скрипт должен быть запущен с правами root"
    echo "Используйте: sudo bash install_nexus.sh"
    exit 1
fi

# Функция для выполнения команд с выводом статуса
run_command() {
    echo "Выполнение: $1"
    if ! eval "$1"; then
        echo "Ошибка при выполнении команды: $1"
        if [ "$2" != "optional" ]; then
            exit 1
        fi
    fi
}

echo "Начало установки..."

# 1. Установка необходимых пакетов
echo "Установка необходимых пакетов..."
run_command "apt update"
run_command "apt install -y unzip curl"

# 2. Удаление старой версии Rust
echo "Удаление старой версии Rust..."
run_command "apt remove -y rustc cargo"
run_command "apt autoremove -y"

# 3. Установка Rust через rustup
echo "Установка Rust..."
run_command 'curl --proto "=https" --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y'
source "$HOME/.cargo/env"

# 4. Установка build-essential
echo "Установка build-essential..."
run_command "apt install -y build-essential"

# 5. Установка pkg-config и libssl-dev
echo "Установка pkg-config и libssl-dev..."
run_command "apt install -y pkg-config libssl-dev"

# 6. Установка protobuf-compiler
echo "Установка Protocol Buffers..."
run_command "apt remove -y protobuf-compiler" "optional"
run_command "mkdir -p /tmp/protoc"
cd /tmp/protoc || exit 1
run_command "curl -LO https://github.com/protocolbuffers/protobuf/releases/download/v21.12/protoc-21.12-linux-x86_64.zip"
run_command "unzip protoc-21.12-linux-x86_64.zip -d /usr/local"
run_command "chmod +x /usr/local/bin/protoc"
run_command "ln -sf /usr/local/bin/protoc /usr/bin/protoc"
cd ~ || exit 1
run_command "rm -rf /tmp/protoc"

# Проверка версий
echo "Проверка установленных версий..."
rustc --version
cargo --version
protoc --version

# Установка Nexus CLI
echo -e "\nУстановка Nexus CLI..."
run_command "rm -rf ~/.nexus/network-api" "optional"
if curl https://cli.nexus.xyz/ | sh; then
    echo -e "\nУстановка успешно завершена!"
else
    echo -e "\nПроизошла ошибка при установке Nexus CLI."
    echo "Проверьте вывод выше на наличие ошибок."
    exit 1
fi