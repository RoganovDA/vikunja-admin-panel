# Vikunja Admin Panel

**Vikunja Admin Panel** — это веб-административная панель, разработанная с использованием Python и Flask, предназначенная для управления пользователями в системе Vikunja. Панель позволяет администраторам входить в систему, просматривать, добавлять, обновлять, удалять, включать и отключать пользователей, а также сбрасывать пароли пользователей. Весь функционал использует CLI команды Vikunja. Установка на той же машине, что и Vikunja

## Функции

- **Система входа** admin admin123
- **Управление пользователями**: создание, редактирование, удаление, включение, отключение пользователей.
- **Сброс пароля** для пользователей.
- **Безопасность**: Хеширование пароля для безопасного хранения.
- **Интеграция с базой данных**: SQLite для хранения учетных данных пользователей.
- **Адаптивный дизайн**: Используется Bootstrap 4 для удобного интерфейса.
- **Модальные формы**: Для добавления, редактирования и удаления пользователей.

## Установка

1. **Установка**:
   ```bash
   apt install -y git python3 python3-pip python3-venv
   /usr/bin/python3 -m pip install flask werkzeug
   cd /home
   git clone https://github.com/RoganovDA/vikunja-admin-panel.git
   sudo chmod -R 755 /home/vikunja-admin-panel

## Добавляем в автозагрузку 
1. **Создаем  vikunja-ap.service**:
   ```bash
   sudo nano /etc/systemd/system/vikunja-ap.service
2. **Вставляем**:
     ```bash                                                            
   [Unit]
   Description=Flask Admin Panel
   After=network.target

   [Service]
   User=root
   WorkingDirectory=/home/vikunja-admin-panel
   ExecStart=/usr/bin/python3 /home/vikunja-admin-panel/app.py
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
3. **Перезапускаем daemon, добавляем в автозапуск и запускаем vikunja-ap.service**:
   > `sudo systemctl daemon-reload`
   
   > `sudo systemctl enable vikunja-ap.service`
   
   > `sudo systemctl start vikunja-ap.service`
   
   > `sudo systemctl status vikunja-ap.service`



