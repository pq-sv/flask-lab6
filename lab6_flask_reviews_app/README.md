# ЛР6. Образовательный портал с отзывами к курсам

## Что реализовано

- Модель `Review` для таблицы `reviews`.
- Отношения `Review.course` и `Review.user`.
- Отображение пяти последних отзывов на странице курса.
- Страница всех отзывов курса `/courses/<course_id>/reviews`.
- Пагинация отзывов.
- Сортировка отзывов: по новизне, сначала положительные, сначала отрицательные.
- Форма создания отзыва на странице курса и странице всех отзывов.
- Если пользователь уже оставил отзыв, вместо формы показывается его отзыв.
- При добавлении отзыва пересчитывается рейтинг курса через `rating_sum` и `rating_num`.
- Тесты для новой функциональности.

## Данные для входа

Логин: `user`

Пароль: `qwerty`

## Локальный запуск

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m pytest tests/
python -m flask run
```

После запуска открой:

```text
http://127.0.0.1:5000/
```

Демонстрационная БД и тестовый курс создаются автоматически при первом запуске.

## Команды миграций по заданию

Если нужно выполнить именно через Flask-Migrate:

```bash
flask db init
flask db migrate -m "Add reviews"
flask db upgrade
```

В модели уже добавлена таблица `reviews`, поэтому миграция создаст нужную таблицу.

## Хостинг Render

Если на GitHub структура такая:

```text
flask-lab6/
├── app/
├── requirements.txt
└── wsgi.py
```

то настройки Render:

```text
Root Directory: пусто
Build Command: pip install -r requirements.txt
Start Command: gunicorn wsgi:app
```

Если ты загрузишь внутрь GitHub дополнительную внешнюю папку, укажи её в `Root Directory`.
