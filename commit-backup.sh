#!/bin/bash

# Загружаем переменные окружения из файла .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    
    # Проверяем обязательные переменные
    if [ -z "$VPS_IP" ] || [ -z "$DIRECTORY" ] || [ -z "$OPENAI_API_KEY" ]; then
        echo "Предупреждение: Отсутствуют обязательные переменные в .env файле"
        echo "Требуются: VPS_IP, DIRECTORY, OPENAI_API_KEY"
    fi
else
    echo "Предупреждение: файл .env не найден."
fi

# Функция для проверки успешного выполнения команды
check_command() {
    if [ $? -ne 0 ]; then
        echo "Ошибка: $1"
        exit 1
    fi
}

# Проверяем необходимые зависимости
for cmd in git jq curl; do
    if ! command -v $cmd &> /dev/null; then
        echo "Ошибка: $cmd не установлен."
        exit 1
    fi
done

# Добавляем изменения и получаем diff
git add .
check_command "Не удалось выполнить 'git add'"

git_diff=$(git diff --cached)

# Если нет изменений, завершаем скрипт
if [ -z "$git_diff" ]; then
    echo "Нет изменений для коммита."
    exit 0
fi

# Определяем описание коммита
diff_length=${#git_diff}
max_diff_length=50000

if [ $diff_length -gt $max_diff_length ] || [ -z "$OPENAI_API_KEY" ]; then
    commit_description="автоматический коммит изменений"
else
    # Генерируем описание с помощью GPT-4
    api_response=$(curl -s https://api.openai.com/v1/chat/completions \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $OPENAI_API_KEY" \
      -d @<(cat <<EOF
    {
      "model": "gpt-4o-mini",
      "messages": [
        {
          "role": "system",
          "content": "Вы - опытный разработчик. Опишите изменения в коде кратко (до 70 слов)."
        },
        {
          "role": "user",
          "content": $(jq -Rs . <<< "$git_diff")
        }
      ],
      "max_tokens": 100
    }
EOF
    ))

    if echo "$api_response" | jq -e '.error' > /dev/null; then
        commit_description="автоматический коммит"
    else
        commit_description=$(echo "$api_response" | jq -r '.choices[0].message.content')
    fi
fi

# Выполняем коммит и пуш
git commit -m "$commit_description"
check_command "Не удалось выполнить коммит"

if ! git push origin main; then
    echo "Push не удался. Пробуем pull и push."
    git pull origin main
    check_command "Не удалось выполнить pull"
    
    git push origin main
    check_command "Не удалось выполнить push после pull"
fi

# Обновляем код на сервере через SSH
ssh -o StrictHostKeyChecking=no root@"$VPS_IP" "
    cd $DIRECTORY || exit
    git fetch origin main
    git reset --hard origin/main
    git clean -fd
    
    # Перезапускаем Docker
    docker-compose down
    docker-compose build --no-cache
    docker-compose up -d
    
    # Перезапускаем Nginx
    systemctl restart nginx
"

# Обновляем зависимости бэкенда
cd src/backend
pip install -r requirements.txt
cd ../..

# Выводим информацию о коммите
commit_hash=$(git rev-parse HEAD)
echo -e "\n\"\"\""
echo "$commit_description"
echo
echo "\`\`\`$commit_hash\`\`\`"
echo
echo "коммиты, общие знания, география, математика, история"
echo "\"\"\""

echo "Все операции успешно выполнены!"

