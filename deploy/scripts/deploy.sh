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

# Переменные
PROJECT_NAME="web_2025"
PROJECT_DIR="/var/www/$PROJECT_NAME"
DB_NAME="${PROJECT_NAME}_db"
DB_USER="${PROJECT_NAME}_user"
DB_PASSWORD=$(openssl rand -base64 32)
DJANGO_SECRET_KEY=$(openssl rand -base64 50)
SERVER_IP=$(hostname -I | awk '{print $1}')

log_info "Начало развертывания проекта $PROJECT_NAME..."
log_info "IP сервера: $SERVER_IP"

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

# Остановка и перезапуск для гарантии
systemctl stop postgresql 2>/dev/null || true
sleep 2

# Создание базы данных и пользователя
sudo -u postgres psql -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>/dev/null || true
sudo -u postgres psql -c "DROP USER IF EXISTS $DB_USER;" 2>/dev/null || true

sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;"
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET timezone TO 'UTC';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

# Настройка безопасности PostgreSQL (только localhost)
log_info "Настройка безопасности PostgreSQL..."
PG_VERSION=$(psql --version 2>/dev/null | awk '{print $3}' | cut -d'.' -f1)
PG_HBA="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"

if [ -f "$PG_HBA" ]; then
    # Разрешаем только localhost для всех баз
    sed -i '/^host.*all.*all.*0\.0\.0\.0\/0.*md5/d' "$PG_HBA"
    sed -i '/^host.*all.*all.*::\/0.*md5/d' "$PG_HBA"
    
    # Убедимся, что есть правило для localhost
    if ! grep -q "host.*all.*all.*127.0.0.1/32.*md5" "$PG_HBA"; then
        echo "host    all             all             127.0.0.1/32            md5" >> "$PG_HBA"
    fi
    
    systemctl restart postgresql
    log_info "PostgreSQL перезапущен с настройками безопасности"
else
    log_warn "Файл pg_hba.conf не найден. Используем стандартную конфигурацию."
    systemctl restart postgresql
fi

# =============================================================================
# ШАГ 3: Копирование проекта
# =============================================================================
log_info "Шаг 3: Подготовка проекта..."

if [ -d "$PROJECT_DIR" ]; then
    log_warn "Директория $PROJECT_DIR уже существует. Очищаем..."
    rm -rf "$PROJECT_DIR"
fi

# Создаем временную директорию для проекта
log_info "Копирование файлов проекта..."
# ВАЖНО: Предполагается, что скрипт запускается из директории с проектом
# или вы указываете правильный путь
SOURCE_DIR=$(pwd)
if [ ! -f "$SOURCE_DIR/manage.py" ]; then
    log_error "Файл manage.py не найден в текущей директории!"
    log_error "Запустите скрипт из корневой директории Django проекта."
    exit 1
fi

mkdir -p "$PROJECT_DIR"
cp -r "$SOURCE_DIR"/* "$PROJECT_DIR"/ 2>/dev/null || true

cd "$PROJECT_DIR"

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
    log_warn "requirements.txt не найден, устанавливаем минимальный набор..."
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
cat << EOF | python manage.py shell
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
ExecStart=$PROJECT_DIR/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 --timeout 120 web_2025.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
ExecStop=/bin/kill -s TERM \$MAINPID
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable gunicorn
systemctl start gunicorn

log_info "Проверка статуса Gunicorn..."
sleep 2
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
# ШАГ 9: Проверка работоспособности
# =============================================================================
log_info "Шаг 9: Проверка работоспособности..."
sleep 5

# Проверка портов
log_info "Проверка открытых портов:"
netstat -tlnp | grep -E ':(80|5432|8000)' || true

# Проверка доступности
log_info "Проверка доступности приложения..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost || echo "000")

if [[ "$HTTP_STATUS" =~ ^(200|301|302|403|404)$ ]]; then
    log_info "✓ Приложение доступно! HTTP статус: $HTTP_STATUS"
else
    log_warn "HTTP статус: $HTTP_STATUS"
    log_warn "Проверьте логи командой: sudo journalctl -u gunicorn -n 30"
fi

# Проверка Pillow
log_info "Проверка установки Pillow..."
if python -c "from PIL import Image; print('Image module loaded')" 2>/dev/null; then
    log_info "✓ Pillow установлен корректно"
else
    log_error "✗ Ошибка при загрузке Pillow"
fi

# =============================================================================
# ШАГ 10: Финальный вывод
# =============================================================================
log_info ""
log_info "================================================"
log_info "РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО!"
log_info "================================================"
log_info "Приложение доступно по адресу: http://$SERVER_IP"
log_info "Админка: http://$SERVER_IP/admin"
log_info "Логин: admin, Пароль: admin123"
log_info ""
log_info "Данные БД:"
log_info "  База: $DB_NAME"
log_info "  Пользователь: $DB_USER"
log_info "  Пароль: $DB_PASSWORD"
log_info ""
log_info "Для проверки с хостовой машины:"
log_info "  curl http://$SERVER_IP"
log_info "  или откройте в браузере"
log_info "================================================"
