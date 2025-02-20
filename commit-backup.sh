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

# Функция для загрузки переменных из .env файла
load_env() {
    if [ -f .env ]; then
        export $(cat .env | grep -v '^#' | xargs)
    else
        echo "Файл .env не найден. Создаю из шаблона..."
        if [ ! -f .env.example ]; then
            echo "GITHUB_TOKEN=your_token_here" > .env.example
        fi
        cp .env.example .env
        echo "Пожалуйста, отредактируйте файл .env и добавьте ваш GitHub токен"
        exit 1
    fi

    # Проверка наличия токена
    if [ -z "$GITHUB_TOKEN" ] || [ "$GITHUB_TOKEN" = "your_token_here" ]; then
        echo "GitHub токен не настроен. Пожалуйста, добавьте его в файл .env"
        exit 1
    fi
}

# Проверка наличия git
if ! command -v git &> /dev/null; then
    echo "Git не установлен. Установите его с помощью:"
    echo "sudo apt update && sudo apt install git"
    exit 1
fi

# Создание .gitignore если его нет
if [ ! -f .gitignore ]; then
    echo "Создание .gitignore..."
    echo ".env" > .gitignore
    run_command "git add .gitignore"
    run_command "git commit -m \"Add .gitignore\""
fi

# Загрузка переменных окружения
load_env

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
    echo "Введите URL удаленного репозитория (в формате: https://github.com/username/repo.git):"
    read -r repo_url
    
    # Формируем URL с токеном
    repo_url_with_token=${repo_url/https:\/\//https:\/\/$GITHUB_TOKEN@}
    run_command "git remote add origin \"$repo_url_with_token\""
fi

# Получение текущей ветки
current_branch=$(git branch --show-current)
if [ -z "$current_branch" ]; then
    current_branch="main"
    run_command "git checkout -b $current_branch"
fi

# Отправка изменений
echo "Отправка изменений в удаленный репозиторий..."
if ! git push origin "$current_branch" 2>/dev/null; then
    echo "Первая отправка в репозиторий..."
    if ! git push -u origin "$current_branch" 2>/dev/null; then
        echo "Ошибка доступа. Проверьте токен в файле .env"
        exit 1
    fi
fi

echo "Резервное копирование успешно завершено!"