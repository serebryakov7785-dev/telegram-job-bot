[README.md](https://github.com/user-attachments/files/25073107/README.md)
[README.md](https://github.com/user-attachments/files/25073107/README.md)
# Telegram Job Bot 🇺🇿

[English](#english) | [Русский](#russian)

---

<a name="english"></a>
## 🇬🇧 English

**Telegram Job Bot** is a comprehensive solution for job searching and recruitment in Uzbekistan, built directly within Telegram. It connects job seekers with employers, providing a seamless experience for creating resumes, posting vacancies, and managing the hiring process.

### 🚀 Features

#### 👤 For Job Seekers
*   **Registration:** Easy sign-up with phone number verification.
*   **Resume Builder:** Create a detailed profile including profession, education, experience, skills, and languages.
*   **Job Search:** Search for vacancies by region and city.
*   **Applications:** Apply for jobs with a single click.
*   **Status Management:** Toggle between "Active Search" and "Found a Job".
*   **Chat:** Communicate directly with employers after an invitation.

#### 🏢 For Employers
*   **Company Profile:** Register your company with contact details.
*   **Vacancy Management:** Create, edit, and delete job postings.
*   **Candidate Search:** Browse active job seekers by location.
*   **Recruitment:** Invite candidates to interviews and manage applications.
*   **Chat:** Communicate with potential hires.

#### 👑 For Administrators
*   **Dashboard:** View real-time statistics (users, vacancies).
*   **Broadcasts:** Send mass messages to all users.
*   **User Management:** Search and view user details.
*   **Moderation:** Handle complaints and bug reports.
*   **Backups:** Create and download database backups directly in the chat.

### 🛠 Tech Stack
*   **Language:** Python 3.8+
*   **Framework:** `pyTelegramBotAPI` (telebot)
*   **Database:** SQLite
*   **Containerization:** Docker & Docker Compose
*   **Monitoring:** Prometheus (Metrics) & Sentry (Error Tracking)

### ⚙️ Installation

#### Prerequisites
*   Docker & Docker Compose
*   Or Python 3.8+

#### 1. Clone the repository
```bash
git clone https://github.com/yourusername/telegram-job-bot.git
cd telegram-job-bot
```

#### 2. Configuration
Create a `.env` file in the root directory:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789,987654321
PROMETHEUS_PORT=8000
SENTRY_DSN=your_sentry_dsn_optional
```

#### 3. Run with Docker (Recommended)
```bash
docker-compose up -d --build
```

#### 4. Run Locally
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run the bot
python bot.py
```

---

<a name="russian"></a>
## 🇷🇺 Русский

**Telegram Job Bot** — это полноценное решение для поиска работы и найма сотрудников в Узбекистане, работающее прямо в Telegram. Бот соединяет соискателей и работодателей, предоставляя удобный интерфейс для создания резюме, публикации вакансий и управления процессом найма.

### 🚀 Возможности

#### 👤 Для Соискателей
*   **Регистрация:** Простая регистрация с подтверждением номера телефона.
*   **Конструктор резюме:** Создание подробного профиля (профессия, образование, опыт, навыки, языки).
*   **Поиск работы:** Поиск вакансий по регионам и городам.
*   **Отклики:** Отклик на вакансии в один клик.
*   **Управление статусом:** Переключение статуса ("Активно ищу" / "Нашел работу").
*   **Чат:** Прямое общение с работодателями после получения приглашения.

#### 🏢 Для Работодателей
*   **Профиль компании:** Регистрация компании с контактными данными.
*   **Управление вакансиями:** Создание, редактирование и удаление вакансий.
*   **Поиск кандидатов:** Просмотр активных соискателей с фильтрацией по локации.
*   **Найм:** Приглашение кандидатов на собеседование и управление откликами.
*   **Чат:** Общение с потенциальными сотрудниками.

#### 👑 Для Администраторов
*   **Дашборд:** Просмотр статистики в реальном времени (пользователи, вакансии).
*   **Рассылки:** Массовая отправка сообщений всем пользователям.
*   **Управление пользователями:** Поиск и просмотр информации о пользователях.
*   **Модерация:** Обработка жалоб и сообщений об ошибках.
*   **Бэкапы:** Создание и скачивание резервных копий базы данных прямо в чате.

### 🛠 Технологический стек
*   **Язык:** Python 3.8+
*   **Фреймворк:** `pyTelegramBotAPI` (telebot)
*   **База данных:** SQLite
*   **Контейнеризация:** Docker & Docker Compose
*   **Мониторинг:** Prometheus (Метрики) и Sentry (Отслеживание ошибок)

### ⚙️ Установка

#### Требования
*   Docker и Docker Compose
*   Или Python 3.8+

#### 1. Клонирование репозитория
```bash
git clone https://github.com/yourusername/telegram-job-bot.git
cd telegram-job-bot
```

#### 2. Настройка
Создайте файл `.env` в корневой директории:
```env
TELEGRAM_BOT_TOKEN=ваш_токен_бота
ADMIN_IDS=123456789,987654321
PROMETHEUS_PORT=8000
SENTRY_DSN=ваш_sentry_dsn_необязательно
```

#### 3. Запуск через Docker (Рекомендуется)
```bash
docker-compose up -d --build
```

#### 4. Локальный запуск
```bash
# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # или venv\Scripts\activate на Windows

# Установка зависимостей
pip install -r requirements.txt

# Запуск бота
python bot.py
```
