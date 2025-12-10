#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}[INFO] Начинаем деплой...${NC}"

# 1. Обновление системы
apt-get update
apt-get upgrade -y

# 2. Установка зависимостей
apt-get install -y \
    python3-pip python3-venv \
    postgresql postgresql-contrib \
    nginx curl git \
    libpq-dev python3-dev

# 3. Создание директории проекта
PROJECT_DIR="/var/www/web_2025"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# 4. Копирование файлов проекта (вместо клонирования!)
cp -r /home/web_fefu_2025/* $PROJECT_DIR/ || true

# 5. Настройка PostgreSQL
DB_NAME="web_2025_db"
DB_USER="web_2025_user"
DB_PASSWORD=$(openssl rand -base64 12)

sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;"
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

# 6. Создание виртуального окружения и установка зависимостей
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 7. Настройка переменных окружения
export DJANGO_ENV=production
export DJANGO_DEBUG=False
export DJANGO_SECRET_KEY=$(openssl rand -base64 50)
export DB_NAME=$DB_NAME
export DB_USER=$DB_USER
export DB_PASSWORD=$DB_PASSWORD

# 8. Миграции и сбор статики
python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear

# 9. Настройка прав
chown -R www-data:www-data $PROJECT_DIR
chmod -R 755 $PROJECT_DIR

# 10. Настройка Gunicorn
cp deploy/systemd/gunicorn.service /etc/systemd/system/
sed -i "s|ваш_пароль_123|$DB_PASSWORD|g" /etc/systemd/system/gunicorn.service
sed -i "s|ваш_секретный_ключ_генерируемый_позже|$DJANGO_SECRET_KEY|g" /etc/systemd/system/gunicorn.service

systemctl daemon-reload
systemctl start gunicorn
systemctl enable gunicorn

# 11. Настройка Nginx
cp deploy/nginx/fefu_lab.conf /etc/nginx/sites-available/
ln -sf /etc/nginx/sites-available/fefu_lab.conf /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

echo -e "${GREEN}[INFO] Деплой завершен!${NC}"
echo "IP адрес: $(hostname -I | awk '{print $1}')"
