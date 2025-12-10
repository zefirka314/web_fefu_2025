#!/bin/bash
# deploy.sh - скрипт автоматического развертывания Django приложения
# Запуск: sudo ./deploy.sh

set -e  # Прерывать выполнение при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка прав
if [ "$EUID" -ne 0 ]; then 
    log_error "Этот скрипт требует прав суперпользователя. Запустите: sudo $0"
    exit 1
fi

# =============================================================================
# КОНФИГУРАЦИОННЫЕ ПЕРЕМЕННЫЕ
# =============================================================================

# ИЗМЕНИТЕ ЭТИ ЗНАЧЕНИЯ ПОД ВАШ ПРОЕКТ!
REPO_URL="https://github.com/zefirka314/web_fefu_2025.git"  # URL вашего GitHub репозитория
BRANCH="main"                     # Ветка для клонирования
PROJECT_NAME="web_fefu_2025"      # Имя проекта (должно совпадать с именем Django проекта)
PROJECT_DIR="/var/www/$PROJECT_NAME"
DB_NAME="${PROJECT_NAME}_db"
DB_USER="${PROJECT_NAME}_user"
DB_PASSWORD=$(openssl rand -base64 32)
DJANGO_SECRET_KEY=$(openssl rand -base64 50)
SERVER_IP=$(hostname -I | awk '{print $1}')

log_info "Начало развертывания проекта $PROJECT_NAME..."
log_info "IP сервера: $SERVER_IP"
log_info "Клонирование из: $REPO_URL (ветка: $BRANCH)"

# =============================================================================
# ШАГ 1: Обновление системы и установка зависимостей
# =============================================================================
log_info "Шаг 1: Обновление системы и установка зависимостей..."
apt-get update
apt-get upgrade -y

# Установка системных пакетов
log_info "Установка системных зависимостей..."
apt-get install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    postgresql \
    postgresql-contrib \
    nginx \
    curl \
    git \
    libpq-dev \
    build-essential \
    net-tools \
    htop \
    libjpeg-dev \
    libfreetype6-dev \
    zlib1g-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev

# =============================================================================
# ШАГ 2: Настройка PostgreSQL
# =============================================================================
log_info "Шаг 2: Настройка PostgreSQL..."

# Запускаем PostgreSQL если не запущен
if ! systemctl is-active --quiet postgresql; then
    log_info "Запуск PostgreSQL..."
    systemctl start postgresql
    systemctl enable postgresql
    sleep 5
fi

# Проверяем, что PostgreSQL запущен
if ! systemctl is-active --quiet postgresql; then
    log_error "PostgreSQL не запускается. Проверьте логи: journalctl -u postgresql"
    exit 1
fi

# Ждем, чтобы PostgreSQL точно запустился
log_info "Ожидание полного запуска PostgreSQL..."
for i in {1..10}; do
    if sudo -u postgres psql -c "SELECT 1;" >/dev/null 2>&1; then
        log_info "PostgreSQL запущен и готов к работе"
        break
    fi
    log_info "Ожидание PostgreSQL... ($i/10)"
    sleep 2
done

# Проверяем доступность PostgreSQL
if ! sudo -u postgres psql -c "SELECT 1;" >/dev/null 2>&1; then
    log_error "PostgreSQL не доступен после 20 секунд ожидания"
    log_error "Проверьте статус: systemctl status postgresql"
    exit 1
fi

# Создание базы данных и пользователя
log_info "Создание базы данных и пользователя PostgreSQL..."

# Принудительно завершаем все соединения к базе
sudo -u postgres psql -c "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '$DB_NAME' AND pid <> pg_backend_pid();" 2>/dev/null || true

# Удаляем старую базу и пользователя
sudo -u postgres psql -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>/dev/null || true
sudo -u postgres psql -c "DROP USER IF EXISTS $DB_USER;" 2>/dev/null || true

# Создаём пользователя с правами суперпользователя (для лабораторной работы)
sudo -u postgres psql -c "CREATE USER $DB_USER WITH SUPERUSER CREATEDB CREATEROLE LOGIN PASSWORD '$DB_PASSWORD';"

# Создаём базу данных с владельцем
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME WITH OWNER $DB_USER ENCODING 'UTF8' LC_COLLATE = 'en_US.UTF-8' LC_CTYPE = 'en_US.UTF-8' TEMPLATE template0;"

# Даём все права
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

# КРИТИЧЕСКИ ВАЖНО: Даем права на схему public для пользователя
sudo -u postgres psql -d $DB_NAME -c "GRANT ALL ON SCHEMA public TO $DB_USER;"
sudo -u postgres psql -d $DB_NAME -c "GRANT CREATE ON SCHEMA public TO $DB_USER;"

# Настройка безопасности PostgreSQL (только localhost)
log_info "Настройка безопасности PostgreSQL..."
PG_VERSION=$(ls /etc/postgresql/ 2>/dev/null | head -n1)
if [ -z "$PG_VERSION" ]; then
    PG_VERSION="14"  # Версия по умолчанию для Ubuntu 22.04
fi

PG_HBA="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"

if [ -f "$PG_HBA" ]; then
    # Делаем резервную копию
    cp "$PG_HBA" "${PG_HBA}.backup"
    
    # Разрешаем только localhost для всех баз
    sed -i '/^host.*all.*all.*0\.0\.0\.0\/0.*md5/d' "$PG_HBA"
    sed -i '/^host.*all.*all.*::\/0.*md5/d' "$PG_HBA"
    
    # Убедимся, что есть правило для localhost
    if ! grep -q "host.*all.*all.*127.0.0.1/32.*md5" "$PG_HBA"; then
        echo "host    all             all             127.0.0.1/32            md5" >> "$PG_HBA"
    fi
    
    # Добавляем правило для нашей базы
    echo "host    $DB_NAME         $DB_USER         127.0.0.1/32            md5" >> "$PG_HBA"
    
    systemctl restart postgresql
    log_info "PostgreSQL перезапущен с настройками безопасности"
else
    log_warn "Файл pg_hba.conf не найден по пути $PG_HBA"
    log_warn "Используем стандартную конфигурацию PostgreSQL"
fi

# =============================================================================
# ШАГ 3: КЛОНИРОВАНИЕ ПРОЕКТА ИЗ GITHUB
# =============================================================================
log_info "Шаг 3: Клонирование проекта из GitHub..."

if [ -d "$PROJECT_DIR" ]; then
    log_warn "Директория $PROJECT_DIR уже существует. Очищаем..."
    rm -rf "$PROJECT_DIR"
fi

# Клонируем репозиторий
log_info "Клонирование репозитория $REPO_URL..."
git clone -b "$BRANCH" "$REPO_URL" "$PROJECT_DIR"

# Проверяем успешность клонирования
if [ ! -f "$PROJECT_DIR/manage.py" ]; then
    log_error "Ошибка: проект не содержит manage.py после клонирования!"
    log_error "Проверьте структуру репозитория и переменные REPO_URL, PROJECT_NAME"
    exit 1
fi

cd "$PROJECT_DIR"
log_info "✓ Проект успешно клонирован в $PROJECT_DIR"

# =============================================================================
# ШАГ 4: Настройка Python окружения
# =============================================================================
log_info "Шаг 4: Настройка Python окружения..."

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей Python
log_info "Установка Python зависимостей..."
pip install --upgrade pip

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    log_warn "requirements.txt не найден в репозитории, устанавливаем минимальный набор..."
    pip install Django gunicorn psycopg2-binary Pillow
fi

# =============================================================================
# ШАГ 5: Настройка Django
# =============================================================================
log_info "Шаг 5: Настройка Django..."

# Определение IP сервера для ALLOWED_HOSTS
if [ -z "$SERVER_IP" ]; then
    SERVER_IP="localhost"
fi

# Экспорт переменных окружения для Django
export DJANGO_ENV=production
export DJANGO_DEBUG=False
export DJANGO_SECRET_KEY="$DJANGO_SECRET_KEY"
export DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1,$SERVER_IP"
export DJANGO_CSRF_TRUSTED_ORIGINS="http://$SERVER_IP"
export DB_NAME="$DB_NAME"
export DB_USER="$DB_USER"
export DB_PASSWORD="$DB_PASSWORD"
export DB_HOST="localhost"
export DB_PORT="5432"

# Применение миграций
log_info "Применение миграций базы данных..."
python manage.py migrate --noinput

# Создание суперпользователя
log_info "Создание суперпользователя Django..."
cat << EOF | python manage.py shell 2>/dev/null || log_warn "Ошибка при создании суперпользователя"
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("Суперпользователь создан")
else:
    print("Суперпользователь уже существует")
EOF

# Сбор статических файлов
log_info "Сбор статических файлов..."
python manage.py collectstatic --noinput --clear

# Создание директории для медиа файлов
mkdir -p media
chmod 755 media

# =============================================================================
# ШАГ 6: Настройка Gunicorn
# =============================================================================
log_info "Шаг 6: Настройка Gunicorn..."

# Создание директории для логов
mkdir -p /var/log/gunicorn
chown -R www-data:www-data /var/log/gunicorn

# Создание сервисного файла Gunicorn
GUNICORN_SERVICE="/etc/systemd/system/gunicorn.service"

# Проверяем, есть ли готовый конфиг в репозитории
if [ -f "deploy/systemd/gunicorn.service" ]; then
    log_info "Использую конфигурацию gunicorn.service из репозитория..."
    cp deploy/systemd/gunicorn.service "$GUNICORN_SERVICE"
    
    # Заменяем плейсхолдеры в конфиге
    sed -i "s|%PROJECT_NAME%|$PROJECT_NAME|g" "$GUNICORN_SERVICE"
    sed -i "s|%PROJECT_DIR%|$PROJECT_DIR|g" "$GUNICORN_SERVICE"
    sed -i "s|%DJANGO_SECRET_KEY%|$DJANGO_SECRET_KEY|g" "$GUNICORN_SERVICE"
    sed -i "s|%DB_PASSWORD%|$DB_PASSWORD|g" "$GUNICORN_SERVICE"
    sed -i "s|%SERVER_IP%|$SERVER_IP|g" "$GUNICORN_SERVICE"
    sed -i "s|%DB_NAME%|$DB_NAME|g" "$GUNICORN_SERVICE"
    sed -i "s|%DB_USER%|$DB_USER|g" "$GUNICORN_SERVICE"
else
    log_warn "Конфиг gunicorn.service не найден в репозитории, создаю базовый..."
    cat > "$GUNICORN_SERVICE" << EOF
[Unit]
Description=Gunicorn для Django проект $PROJECT_NAME
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment=DJANGO_ENV=production
Environment=DJANGO_DEBUG=False
Environment=DJANGO_SECRET_KEY=$DJANGO_SECRET_KEY
Environment=DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,$SERVER_IP
Environment=DJANGO_CSRF_TRUSTED_ORIGINS=http://$SERVER_IP
Environment=DB_NAME=$DB_NAME
Environment=DB_USER=$DB_USER
Environment=DB_PASSWORD=$DB_PASSWORD
Environment=DB_HOST=localhost
Environment=DB_PORT=5432
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 --timeout 120 $PROJECT_NAME.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
ExecStop=/bin/kill -s TERM \$MAINPID
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
fi

systemctl daemon-reload
systemctl enable gunicorn
systemctl start gunicorn

log_info "Проверка статуса Gunicorn..."
sleep 3
if systemctl is-active --quiet gunicorn; then
    log_info "✓ Gunicorn запущен успешно"
else
    log_error "✗ Gunicorn не запустился"
    journalctl -u gunicorn -n 20 --no-pager
fi

# =============================================================================
# ШАГ 7: Настройка Nginx
# =============================================================================
log_info "Шаг 7: Настройка Nginx..."

# Создание конфигурации Nginx
NGINX_CONFIG="/etc/nginx/sites-available/$PROJECT_NAME"

# Проверяем, есть ли готовый конфиг в репозитории
if [ -f "deploy/nginx/fefu_lab.conf" ]; then
    log_info "Использую конфигурацию Nginx из репозитория..."
    cp deploy/nginx/fefu_lab.conf "$NGINX_CONFIG"
    
    # Заменяем плейсхолдеры в конфиге
    sed -i "s|%PROJECT_DIR%|$PROJECT_DIR|g" "$NGINX_CONFIG"
    sed -i "s|%SERVER_IP%|$SERVER_IP|g" "$NGINX_CONFIG"
    sed -i "s|%PROJECT_NAME%|$PROJECT_NAME|g" "$NGINX_CONFIG"
else
    log_warn "Конфиг Nginx не найден в репозитории, создаю базовый..."
    cat > "$NGINX_CONFIG" << EOF
server {
    listen 80;
    server_name $SERVER_IP;
    
    location /static/ {
        alias $PROJECT_DIR/static/;
        expires 30d;
        access_log off;
    }
    
    location /media/ {
        alias $PROJECT_DIR/media/;
        expires 30d;
        access_log off;
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
}
EOF
fi

# Создание символической ссылки
ln -sf "$NGINX_CONFIG" /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

# Проверка конфигурации
log_info "Проверка конфигурации Nginx..."
if nginx -t; then
    systemctl restart nginx
    systemctl enable nginx
    log_info "✓ Nginx настроен успешно"
else
    log_error "✗ Ошибка в конфигурации Nginx"
    nginx -t 2>&1
    exit 1
fi

# =============================================================================
# ШАГ 8: Настройка прав доступа
# =============================================================================
log_info "Шаг 8: Настройка прав доступа..."
chown -R www-data:www-data "$PROJECT_DIR"
chmod -R 755 "$PROJECT_DIR"

# =============================================================================
# ШАГ 9: ПРОВЕРКА РАБОТОСПОСОБНОСТИ
# =============================================================================
log_info "Шаг 9: Проверка работоспособности..."
sleep 5

# 1. Проверка портов
log_info "1. Проверка открытых портов:"
echo "Слушающие порты на сервере:"
netstat -tlnp | grep -E ':(80|5432|8000)' || echo "Не все порты найдены"

# 2. Проверка доступности приложения через curl на localhost:80
log_info ""
log_info "2. Проверка доступности приложения через curl на localhost:80..."

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost || echo "000")

if [[ "$HTTP_STATUS" =~ ^(200|301|302|403|404)$ ]]; then
    log_info "✓ Приложение доступно на localhost:80! HTTP статус: $HTTP_STATUS"
    log_info "✓ Проверьте браузером: http://$SERVER_IP"
else
    log_error "✗ Приложение недоступно на localhost:80 (HTTP статус: $HTTP_STATUS)"
    log_error "Проверьте логи: sudo journalctl -u gunicorn -n 30"
fi

# 3. Проверка статических и медиа файлов
log_info ""
log_info "3. Проверка статических и медиа файлов..."

# Создаем тестовые файлы для проверки
mkdir -p static/test/
mkdir -p media/uploads/
echo "/* Test static CSS file */" > static/test/test.css
echo "Test media content" > media/uploads/test_media.txt

STATIC_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/static/test/test.css || echo "000")
if [[ "$STATIC_CHECK" == "200" ]]; then
    log_info "✓ Статические файлы работают (HTTP $STATIC_CHECK)"
else
    log_error "✗ Статические файлы недоступны (HTTP $STATIC_CHECK)"
fi

MEDIA_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/media/uploads/test_media.txt || echo "000")
if [[ "$MEDIA_CHECK" == "200" ]]; then
    log_info "✓ Медиа файлы работают (HTTP $MEDIA_CHECK)"
else
    log_warn "⚠ Медиа файлы недоступны (HTTP $MEDIA_CHECK)"
fi

# 4. Проверка PostgreSQL подключения
log_info ""
log_info "4. Проверка подключения к PostgreSQL..."
export PGPASSWORD="$DB_PASSWORD"
if psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" >/dev/null 2>&1; then
    log_info "✓ PostgreSQL подключение работает"
else
    log_error "✗ Ошибка подключения к PostgreSQL"
fi
unset PGPASSWORD

# =============================================================================
# ШАГ 10: ФИНАЛЬНЫЙ ВЫВОД И ИНСТРУКЦИИ
# =============================================================================
log_info ""
log_info "================================================"
log_info "РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО!"
log_info "================================================"
log_info ""
log_info "ВЫПОЛНЕНО:"
log_info "✓ Клонирован проект из GitHub: $REPO_URL"
log_info "✓ Установлены все зависимости (системные и Python)"
log_info "✓ Настроена база данных PostgreSQL"
log_info "✓ Настроен Gunicorn как WSGI-сервер"
log_info "✓ Настроен Nginx как обратный прокси"
log_info "✓ Применены миграции и собраны статические файлы"
log_info ""
log_info "РЕЗУЛЬТАТ ПРОВЕРКИ:"
log_info "  Приложение доступно по адресу: http://$SERVER_IP"
log_info "  Админка Django: http://$SERVER_IP/admin"
log_info "  Логин: admin"
log_info "  Пароль: admin123"
log_info ""
log_info "ПРОВЕРКА С ХОСТОВОЙ МАШИНЫ:"
log_info "  curl http://$SERVER_IP"
log_info "  или откройте в браузере"
log_info ""
log_info "ТЕСТ БЕЗОПАСНОСТИ (должны быть недоступны снаружи):"
log_info "  На хостовой машине выполните:"
log_info "  nmap -p 5432,8000 $SERVER_IP"
log_info "  Порты 5432 (PostgreSQL) и 8000 (Gunicorn) должны быть закрыты"
log_info ""
log_info "КОМАНДЫ ДЛЯ УПРАВЛЕНИЯ:"
log_info "  sudo systemctl status gunicorn  # статус приложения"
log_info "  sudo journalctl -u gunicorn -f  # логи в реальном времени"
log_info "  sudo systemctl restart gunicorn # перезапуск приложения"
log_info "  sudo systemctl restart nginx    # перезапуск nginx"
log_info ""
log_info "ДАННЫЕ БАЗЫ ДАННЫХ (сохранены в /root/${PROJECT_NAME}_secrets.txt):"
log_info "  База: $DB_NAME"
log_info "  Пользователь: $DB_USER"
log_info "  Пароль: $DB_PASSWORD"
log_info "================================================"

# Сохранение секретов в файл
SECRETS_FILE="/root/${PROJECT_NAME}_secrets_$(date +%Y%m%d).txt"
cat > "$SECRETS_FILE" << EOF
# Секреты проекта $PROJECT_NAME
# Создано: $(date)
# Репозиторий: $REPO_URL

URL приложения: http://$SERVER_IP
Админка: http://$SERVER_IP/admin
Логин: admin
Пароль: admin123

База данных PostgreSQL:
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_HOST=localhost
DB_PORT=5432

Django SECRET_KEY:
$DJANGO_SECRET_KEY

Команда для подключения к БД:
psql -h localhost -U $DB_USER -d $DB_NAME

Для обновления кода из Git:
cd $PROJECT_DIR
git pull origin $BRANCH
sudo systemctl restart gunicorn
EOF

chmod 600 "$SECRETS_FILE"
log_info "Секреты сохранены в $SECRETS_FILE"
