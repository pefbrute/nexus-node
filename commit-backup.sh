#!/bin/bash

# Проверка наличия аргумента с сообщением коммита
if [ $# -eq 0 ]; then
    echo "Использование: $0 \"сообщение коммита\""
    exit 1
fi

# Функция для выполнения команд с проверкой ошибок
run_command() {
    echo "Выполнение: $1"
    if ! eval "$1"; then
        echo "Ошибка при выполнении команды: $1"
        exit 1
    fi
}

# Проверка наличия git
if ! command -v git &> /dev/null; then
    echo "Git не установлен. Установите его с помощью:"
    echo "sudo apt update && sudo apt install git"
    exit 1
fi

# Проверка, находимся ли мы в git репозитории
if ! git rev-parse --is-inside-work-tree &> /dev/null; then
    echo "Текущая директория не является git репозиторием."
    echo "Инициализируем новый репозиторий..."
    run_command "git init"
    
    # Проверяем настройки git
    if [ -z "$(git config --global user.name)" ]; then
        echo "Введите ваше имя для Git:"
        read -r git_name
        run_command "git config --global user.name \"$git_name\""
    fi
    
    if [ -z "$(git config --global user.email)" ]; then
        echo "Введите ваш email для Git:"
        read -r git_email
        run_command "git config --global user.email \"$git_email\""
    fi
fi

# Добавление всех изменений
echo "Добавление изменений в индекс..."
run_command "git add ."

# Создание коммита
echo "Создание коммита..."
run_command "git commit -m \"$1\""

# Проверка наличия удаленного репозитория
if ! git remote -v | grep origin &> /dev/null; then
    echo "Удаленный репозиторий не настроен."
    echo "Введите URL удаленного репозитория (например, https://github.com/username/repo.git):"
    read -r repo_url
    run_command "git remote add origin $repo_url"
fi

# Получение текущей ветки
current_branch=$(git branch --show-current)
if [ -z "$current_branch" ]; then
    current_branch="main"
    run_command "git checkout -b $current_branch"
fi

# Отправка изменений
echo "Отправка изменений в удаленный репозиторий..."
if ! git push origin "$current_branch"; then
    echo "Первая отправка в репозиторий..."
    run_command "git push -u origin $current_branch"
fi

echo "Резервное копирование успешно завершено!" 