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

# Получаем размер RAM
TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
RECOMMENDED_SWAP=$((TOTAL_RAM * 2))

# Проверяем, достаточно ли места на диске
FREE_SPACE=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
if [ $FREE_SPACE -lt $((SWAP_SIZE + 5)) ]; then
    echo "Внимание: недостаточно места на диске. Доступно: ${FREE_SPACE}G"
    echo "Требуется: $((SWAP_SIZE + 5))G (включая буфер 5G)"
    exit 1
fi

echo "Начало настройки swap..."

# Отключаем и удаляем старый swap если он есть
echo "Отключаем существующий swap..."
swapoff -a
check_command "Не удалось отключить swap"

echo "Удаляем старый swap-файл..."
rm -f /swapfile
check_command "Не удалось удалить старый swap-файл"

# Создаём новый swap-файл с оптимальным размером блока
echo "Создаём новый swap-файл размером ${SWAP_SIZE}GB..."
dd if=/dev/zero of=/swapfile bs=1M count=$((${SWAP_SIZE}*1024)) status=progress
check_command "Не удалось создать swap-файл"

# Настраиваем права и активируем
echo "Настраиваем права доступа..."
chmod 600 /swapfile
check_command "Не удалось установить права доступа"

echo "Форматируем как swap..."
mkswap -f /swapfile
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

# Оптимизация параметров свопинга
echo "Оптимизируем параметры свопинга..."

# Настраиваем swappiness в зависимости от RAM
if [ $TOTAL_RAM -gt 16 ]; then
    SWAPPINESS=10
elif [ $TOTAL_RAM -gt 8 ]; then
    SWAPPINESS=20
else
    SWAPPINESS=30
fi

# Применяем оптимизированные настройки
cat > /etc/sysctl.d/99-swap.conf << EOF
# Уменьшаем использование swap
vm.swappiness=$SWAPPINESS

# Оптимизируем кэширование
vm.vfs_cache_pressure=50
vm.dirty_background_ratio=5
vm.dirty_ratio=10

# Оптимизируем использование памяти
vm.min_free_kbytes=$((TOTAL_RAM * 1024 * 5))
vm.zone_reclaim_mode=0
vm.page-cluster=0

# Настройка OOM killer
vm.oom_kill_allocating_task=1
EOF

# Применяем настройки
sysctl -p /etc/sysctl.d/99-swap.conf

# Выводим информацию о результате
echo -e "\nНастройка swap завершена!"
echo "Текущее состояние памяти:"
free -h

echo -e "\nПараметры свопинга:"
echo "Swappiness: $(cat /proc/sys/vm/swappiness)"
echo "VFS Cache Pressure: $(cat /proc/sys/vm/vfs_cache_pressure)"
echo "Dirty Background Ratio: $(cat /proc/sys/vm/dirty_background_ratio)"
echo "Dirty Ratio: $(cat /proc/sys/vm/dirty_ratio)"

echo -e "\nРекомендуемый размер swap: ${RECOMMENDED_SWAP}G"
echo "Установленный размер swap: ${SWAP_SIZE}G" 