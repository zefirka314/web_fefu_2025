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

# Настраиваем параметры пользователя
sudo -u postgres psql -c "ALTER USER $DB_USER WITH CREATEDB CREATEROLE;"

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

# Проверка подключения к базе данных
log_info "Проверка подключения к базе данных..."
export PGPASSWORD="$DB_PASSWORD"
if psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" >/dev/null 2>&1; then
    log_info "✓ Пользователь $DB_USER успешно подключился к базе $DB_NAME"
else
    log_error "✗ Ошибка подключения пользователя $DB_USER к базе $DB_NAME"
    log_error "Проверьте пароль и права доступа"
    exit 1
fi
unset PGPASSWORD

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
echo "Слушающие порты на сервере:"
netstat -tlnp | grep -E ':(80|5432|8000)' || echo "Не все порты найдены"

# Проверка доступности
log_info "Проверка доступности приложения..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost || echo "000")

if [[ "$HTTP_STATUS" =~ ^(200|301|302|403|404)$ ]]; then
    log_info "✓ Приложение доступно! HTTP статус: $HTTP_STATUS"
    log_info "✓ Проверьте браузером: http://$SERVER_IP"
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

# Проверка PostgreSQL подключения с приложения
log_info "Проверка подключения Django к PostgreSQL..."
if python -c "
import django
from django.conf import settings
if not settings.configured:
    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': '$DB_NAME',
                'USER': '$DB_USER',
                'PASSWORD': '$DB_PASSWORD',
                'HOST': 'localhost',
                'PORT': '5432',
            }
        }
    )
django.setup()
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('SELECT 1')
print('✓ Django может подключиться к PostgreSQL')
" 2>/dev/null; then
    log_info "✓ Django успешно подключается к PostgreSQL"
else
    log_error "✗ Ошибка подключения Django к PostgreSQL"
fi

# =============================================================================
# ШАГ 10: Финальный вывод и проверка безопасности
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
log_info "Проверка безопасности:"
log_info "  PostgreSQL слушает только на 127.0.0.1:5432"
log_info "  Gunicorn слушает только на 127.0.0.1:8000"
log_info "  Nginx слушает на 0.0.0.0:80 (публично)"
log_info ""
log_info "Для проверки с хостовой машины:"
log_info "  curl http://$SERVER_IP"
log_info "  или откройте в браузере: http://$SERVER_IP"
log_info ""
log_info "Для проверки недоступности портов снаружи:"
log_info "  На хостовой машине выполните:"
log_info "  nmap -p 5432,8000 $SERVER_IP"
log_info "  Порты 5432 и 8000 должны быть закрыты (filtered)"
log_info ""
log_info "Команды управления:"
log_info "  sudo systemctl status gunicorn  # статус приложения"
log_info "  sudo journalctl -u gunicorn -f  # логи в реальном времени"
log_info "  sudo systemctl restart gunicorn # перезапуск приложения"
log_info "  sudo systemctl restart nginx    # перезапуск nginx"
log_info "================================================"

# Сохранение секретов в файл (для документации)
SECRETS_FILE="/root/${PROJECT_NAME}_secrets_$(date +%Y%m%d).txt"
cat > "$SECRETS_FILE" << EOF
# Секреты проекта $PROJECT_NAME
# Создано: $(date)

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

Для подключения к БД:
psql -h localhost -U $DB_USER -d $DB_NAME

Для проверки портов:
nmap -p 5432,8000 $SERVER_IP
EOF

chmod 600 "$SECRETS_FILE"
log_info "Секреты сохранены в $SECRETS_FILE"

log_info ""
log_info "Теперь проверьте работу приложения с хостовой машины!"
log_info "Если что-то не работает, проверьте логи:"
log_info "  sudo journalctl -u gunicorn -n 50"
log_info "  sudo tail -f /var/log/nginx/error.log"
