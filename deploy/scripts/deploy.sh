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
REPO_URL="https://github.com/ваш_username/ваш_репозиторий.git"  # ИЗМЕНИТЕ НА СВОЙ
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

# Установка системных пакетов (включая зависимости для Pillow)
log_info "Установка системных зависимостей для Pillow..."
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
    # Зависимости для Pillow (ImageField):
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
PG_VERSION=$(psql --version | awk '{print $3}' | cut -d'.' -f1)
PG_HBA="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"

if [ -f "$PG_HBA" ]; then
    # Резервное копирование оригинального файла
    cp "$PG_HBA" "${PG_HBA}.backup"
    
    # Разрешаем только localhost для всех баз
    sed -i '/^host.*all.*all.*0\.0\.0\.0\/0.*md5/d' "$PG_HBA"
    sed -i '/^host.*all.*all.*::\/0.*md5/d' "$PG_HBA"
    
    # Убедимся, что есть правило для localhost
    if ! grep -q "host.*all.*all.*127.0.0.1/32.*md5" "$PG_HBA"; then
        echo "host    all             all             127.0.0.1/32            md5" >> "$PG_HBA"
    fi
    
    # Разрешаем подключение нашей базы данных
    echo "host    $DB_NAME         $DB_USER         127.0.0.1/32            md5" >> "$PG_HBA"
    
    systemctl start postgresql
    systemctl restart postgresql
    log_info "PostgreSQL перезапущен с настройками безопасности"
else
    log_warn "Файл $PG_HBA не найден. Проверьте версию PostgreSQL."
    systemctl start postgresql
fi

# =============================================================================
# ШАГ 3: Получение кода приложения
# =============================================================================
log_info "Шаг 3: Получение кода приложения..."

if [ -d "$PROJECT_DIR" ]; then
    log_warn "Директория $PROJECT_DIR уже существует. Создаем резервную копию..."
    BACKUP_DIR="/var/backups/$PROJECT_NAME-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    cp -r "$PROJECT_DIR" "$BACKUP_DIR/" 2>/dev/null || true
    rm -rf "$PROJECT_DIR"
fi

# Создаем директорию и копируем файлы
mkdir -p "$PROJECT_DIR"

# Если есть Git репозиторий, клонируем
if [ -n "$REPO_URL" ] && [ "$REPO_URL" != "https://github.com/ваш_username/ваш_репозиторий.git" ]; then
    log_info "Клонирование репозитория из $REPO_URL..."
    git clone "$REPO_URL" "$PROJECT_DIR"
else
    log_warn "Репозиторий не указан. Скопируйте файлы проекта в $PROJECT_DIR вручную."
    log_warn "Запустите: sudo cp -r /путь/к/вашему/проекту/* $PROJECT_DIR/"
    mkdir -p "$PROJECT_DIR"
fi

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
pip install --upgrade pip setuptools wheel

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    # Устанавливаем минимальный набор
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

# Создание .env файла (опционально)
ENV_FILE="$PROJECT_DIR/.env"
cat > "$ENV_FILE" << EOF
# Django Settings
DJANGO_ENV=production
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=$DJANGO_SECRET_KEY
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,$SERVER_IP
DJANGO_CSRF_TRUSTED_ORIGINS=http://$SERVER_IP

# Database
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_HOST=localhost
DB_PORT=5432
EOF

chmod 600 "$ENV_FILE"

# Применение миграций
log_info "Применение миграций базы данных..."
python manage.py migrate --noinput

# Создание суперпользователя (если нет)
log_info "Создание суперпользователя Django..."
echo "from django.contrib.auth import get_user_model; User = get_user_model(); \
User.objects.create_superuser('admin', 'admin@example.com', 'admin123')" \
| python manage.py shell 2>/dev/null || \
log_warn "Суперпользователь уже существует или произошла ошибка"

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

# Копирование и настройка сервисного файла Gunicorn
GUNICORN_SERVICE="/etc/systemd/system/gunicorn.service"
if [ -f "deploy/systemd/gunicorn.service" ]; then
    cp deploy/systemd/gunicorn.service "$GUNICORN_SERVICE"
    
    # Заменяем плейсхолдеры на реальные значения
    sed -i "s|ваш_секретный_ключ_генерируемый_позже|$DJANGO_SECRET_KEY|g" "$GUNICORN_SERVICE"
    sed -i "s|ваш_пароль_123|$DB_PASSWORD|g" "$GUNICORN_SERVICE"
    sed -i "s|ваш_IP_адрес|$SERVER_IP|g" "$GUNICORN_SERVICE"
    
    # Перезагрузка systemd и запуск сервиса
    systemctl daemon-reload
    systemctl enable gunicorn
    systemctl start gunicorn
    
    log_info "Проверка статуса Gunicorn..."
    sleep 2
    systemctl status gunicorn --no-pager | head -20
else
    log_error "Файл gunicorn.service не найден в deploy/systemd/"
    log_info "Создаем базовый конфиг gunicorn.service..."
    
    # Создаем базовый конфиг
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
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 web_2025.wsgi:application
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable gunicorn
    systemctl start gunicorn
fi

# =============================================================================
# ШАГ 7: Настройка Nginx
# =============================================================================
log_info "Шаг 7: Настройка Nginx..."

# Останавливаем Nginx если запущен
systemctl stop nginx 2>/dev/null || true

# Копирование конфигурации Nginx
if [ -f "deploy/nginx/fefu_lab.conf" ]; then
    cp deploy/nginx/fefu_lab.conf /etc/nginx/sites-available/$PROJECT_NAME
    
    # Обновляем server_name в конфиге
    sed -i "s|server_name _;|server_name $SERVER_IP;|g" /etc/nginx/sites-available/$PROJECT_NAME
    
    # Создание символической ссылки
    ln -sf /etc/nginx/sites-available/$PROJECT_NAME /etc/nginx/sites-enabled/
    
    # Удаление дефолтного конфига
    rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
    
    # Проверка конфигурации
    log_info "Проверка конфигурации Nginx..."
    if nginx -t; then
        # Запуск и включение автозагрузки Nginx
        systemctl start nginx
        systemctl enable nginx
        
        log_info "Проверка статуса Nginx..."
        sleep 2
        systemctl status nginx --no-pager | head -10
    else
        log_error "Ошибка в конфигурации Nginx"
        nginx -t 2>&1
    fi
else
    log_error "Конфигурационный файл Nginx не найден в deploy/nginx/"
    log_info "Создаем базовый конфиг Nginx..."
    
    cat > /etc/nginx/sites-available/$PROJECT_NAME << EOF
server {
    listen 80;
    server_name $SERVER_IP;
    
    location /static/ {
        alias $PROJECT_DIR/static/;
        expires 30d;
    }
    
    location /media/ {
        alias $PROJECT_DIR/media/;
        expires 30d;
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
    
    ln -sf /etc/nginx/sites-available/$PROJECT_NAME /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    nginx -t
    systemctl start nginx
    systemctl enable nginx
fi

# =============================================================================
# ШАГ 8: Настройка прав доступа
# =============================================================================
log_info "Шаг 8: Настройка прав доступа..."

# Установка владельца для всех файлов проекта
chown -R www-data:www-data "$PROJECT_DIR"
chmod -R 755 "$PROJECT_DIR"

# Особые права для чувствительных файлов
chmod 600 "$ENV_FILE" 2>/dev/null || true
chmod 600 "$PROJECT_DIR/.env" 2>/dev/null || true

# =============================================================================
# ШАГ 9: Проверка работоспособности
# =============================================================================
log_info "Шаг 9: Проверка работоспособности..."

# Ждем запуска сервисов
sleep 5

# Проверка портов
log_info "Проверка открытых портов..."
echo "Слушающие порты:"
netstat -tlnp | grep -E ':(80|5432|8000)' || log_warn "Не все порты найдены"

# Проверка доступности через curl
log_info "Проверка доступности приложения..."
MAX_RETRIES=5
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost || echo "000")
    
    if [[ "$HTTP_STATUS" =~ ^(200|301|302|403|404)$ ]]; then
        log_info "✓ Приложение доступно! HTTP статус: $HTTP_STATUS"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT+1))
        log_warn "Попытка $RETRY_COUNT/$MAX_RETRIES: HTTP статус $HTTP_STATUS"
        sleep 3
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    log_error "✗ Приложение недоступно после $MAX_RETRIES попыток"
    log_error "Проверьте логи:"
    journalctl -u gunicorn -n 30 --no-pager
    journalctl -u nginx -n 30 --no-pager
fi

# Проверка базы данных
log_info "Проверка подключения к базе данных..."
if sudo -u postgres psql -d "$DB_NAME" -c "SELECT 1;" >/dev/null 2>&1; then
    log_info "✓ База данных доступна"
else
    log_error "✗ Ошибка подключения к БД"
fi

# Проверка Pillow
log_info "Проверка установки Pillow..."
python -c "from PIL import Image; print('✓ Pillow установлен корректно')" 2>/dev/null || \
log_error "✗ Pillow не установлен или есть ошибки"

# =============================================================================
# ШАГ 10: Финальный вывод
# =============================================================================
log_info ""
log_info "================================================"
log_info "РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО!"
log_info "================================================"
log_info ""
log_info "Данные для доступа:"
log_info "  • IP адрес сервера: $SERVER_IP"
log_info "  • URL приложения: http://$SERVER_IP"
log_info "  • Админка: http://$SERVER_IP/admin"
log_info ""
log_info "Учетные данные:"
log_info "  • Логин: admin"
log_info "  • Пароль: admin123"
log_info ""
log_info "Данные базы данных:"
log_info "  • Имя БД: $DB_NAME"
log_info "  • Пользователь: $DB_USER"
log_info "  • Пароль: $DB_PASSWORD"
log_info ""
log_info "Команды для управления:"
log_info "  • Статус: sudo systemctl status gunicorn"
log_info "  • Логи: sudo journalctl -u gunicorn -f"
log_info "  • Перезапуск: sudo systemctl restart gunicorn"
log_info ""
log_info "Проверка с хостовой машины:"
log_info "  curl http://$SERVER_IP"
log_info "  или откройте в браузере: http://$SERVER_IP"
log_info "================================================"

# Сохраняем пароли в безопасное место
SECRETS_FILE="/root/${PROJECT_NAME}_secrets_$(date +%Y%m%d).txt"
cat > "$SECRETS_FILE" << EOF
# Секреты проекта $PROJECT_NAME
# Создано: $(date)

URL приложения: http://$SERVER_IP
Админка: http://$SERVER_IP/admin
Логин: admin
Пароль: admin123

База данных:
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_HOST=localhost
DB_PORT=5432

Django SECRET_KEY:
$DJANGO_SECRET_KEY
EOF

chmod 600 "$SECRETS_FILE"
log_info "Секреты сохранены в $SECRETS_FILE"

log_info ""
log_info "Проверьте, что порты 5432 и 8000 закрыты снаружи:"
log_info "  На хостовой машине выполните: nmap -p 5432,8000 $SERVER_IP"
log_info ""
log_info "Для миграции данных из SQLite в PostgreSQL используйте:"
log_info "  python manage.py dumpdata --exclude=auth.permission --exclude=contenttypes > datadump.json"
log_info "  python manage.py loaddata datadump.json"
