#!/bin/bash

# Проверка root прав
if [ "$EUID" -ne 0 ]; then 
    echo "Этот скрипт должен быть запущен с правами root"
    echo "Используйте: sudo bash setup_swap.sh"
    exit 1
fi

# Функция для проверки успешного выполнения команды
check_command() {
    if [ $? -ne 0 ]; then
        echo "Ошибка: $1"
        exit 1
    fi
}

# Размер swap в гигабайтах
SWAP_SIZE=16

echo "Начало настройки swap..."

# Отключаем и удаляем старый swap если он есть
echo "Отключаем существующий swap..."
swapoff -a
check_command "Не удалось отключить swap"

echo "Удаляем старый swap-файл..."
rm -f /swapfile
check_command "Не удалось удалить старый swap-файл"

# Создаём новый swap-файл
echo "Создаём новый swap-файл размером ${SWAP_SIZE}GB..."
fallocate -l ${SWAP_SIZE}G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=$((${SWAP_SIZE}*1024))
check_command "Не удалось создать swap-файл"

# Настраиваем права и активируем
echo "Настраиваем права доступа..."
chmod 600 /swapfile
check_command "Не удалось установить права доступа"

echo "Форматируем как swap..."
mkswap /swapfile
check_command "Не удалось отформатировать swap"

echo "Активируем swap..."
swapon /swapfile
check_command "Не удалось активировать swap"

# Настраиваем автозагрузку
echo "Настраиваем автозагрузку..."
if ! grep -q "/swapfile none swap sw 0 0" /etc/fstab; then
    echo "/swapfile none swap sw 0 0" >> /etc/fstab
    check_command "Не удалось добавить запись в /etc/fstab"
fi

# Настраиваем параметры свопинга
echo "Оптимизируем параметры свопинга..."
sysctl vm.swappiness=10
sysctl vm.vfs_cache_pressure=50

# Сохраняем параметры свопинга
if ! grep -q "vm.swappiness" /etc/sysctl.conf; then
    echo "vm.swappiness=10" >> /etc/sysctl.conf
    echo "vm.vfs_cache_pressure=50" >> /etc/sysctl.conf
fi

# Выводим информацию о результате
echo -e "\nНастройка swap завершена!"
echo "Текущее состояние памяти:"
free -h

echo -e "\nПараметры свопинга:"
echo "Swappiness: $(cat /proc/sys/vm/swappiness)"
echo "VFS Cache Pressure: $(cat /proc/sys/vm/vfs_cache_pressure)" 