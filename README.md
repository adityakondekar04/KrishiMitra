# Krishi Mitra — Community Education Platform 🌾🤝

Welcome to Krishi Mitra (Agriculture Community Education Platform), a Django-based web application that provides farmers with community features, weather, learning resources, and discussion forums.

This repository contains the web app used for coursework and practical assignments. The project is designed to be approachable for contributors and instructors alike.

---

## 🚀 Quick Overview

- Name: Krishi Mitra
- Framework: Django
- Purpose: Community platform for farmers with forums, profiles, weather info, and learning content.

## 📚 Table of Contents

1. Features
2. Tech stack
3. Quick start (dev)
4. Environment & configuration
5. Testing
6. Contributing
7. License
8. Contact

---

## ✨ Features

- User registration, login, and profiles
- Forum with posts, comments, likes, and threaded replies
- Avatar upload and profile editing
- Weather integration (weather_client)
- Gemini client (gemini_client.py) placeholder for integrations
- Media handling for avatars, forum images, and posts

## 🛠 Tech Stack

- Python 3.x
- Django
- SQLite (default local DB: `db.sqlite3`)
- HTML/CSS/JavaScript for front-end templates (`templates/` + `static/`)

## ⚡ Quick start (development)

Follow these steps to run the project locally on Windows (PowerShell):

1. Create and activate a virtual environment

```powershell
python -m venv venv
& .\venv\Scripts\Activate.ps1
```

2. Install dependencies

If you have a `requirements.txt`, run:

```powershell
pip install -r requirements.txt
```

If the project doesn't have a `requirements.txt`, install Django:

```powershell
pip install django
```

3. Run database migrations and create a superuser

```powershell
python manage.py migrate
python manage.py createsuperuser
```

4. Run the development server

```powershell
python manage.py runserver
```

Then open http://127.0.0.1:8000 in your browser.

## 🔧 Environment & configuration

- Database: By default the project uses `db.sqlite3` in the repo root for convenience.
- Media: Uploaded media is stored under `media/` (avatars, forum media). Ensure the `media/` directory is writable.
- Static files: `static/` contains CSS and JS used by the templates.

If you want to run the app using a `.env` file, create one at the project root and set values like:

```text
# .env (example)
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```

Note: This project includes some example clients (`weather_client.py`, `gemini_client.py`) — update credentials or API keys in environment variables when needed.

## ✅ Testing

This repo includes Django tests in `agrimitra/tests.py` — run them with:

```powershell
python manage.py test
```

If tests are slow or failing locally, first make sure migrations were applied and the virtual environment has required packages installed.

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch: `git checkout -b my-feature`
3. Make changes and add tests where appropriate
4. Commit and push to your fork and open a Pull Request

If you'd like me to push this README for you and open a PR against `main`, say so and I will (I already pushed your local project to `krishi_mitra_local_main`).

## 🧾 License

This project includes a `LICENSE` file. Please review it for license details.

## 📬 Contact

If you need help, reach out to the project owner or maintainers listed in the repository. Happy farming and coding! 🌱👩‍🌾👨‍🌾

Made with ❤️ — Krishi Mitra Team

## 🙌 Contributors

Thank you to the contributors who built this project:

- Sarthak Patil
- Aditya Pundlik    
- Aditya Kondekar
- Omkar Patole

