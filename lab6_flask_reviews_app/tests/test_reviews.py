import pytest

from app import create_app
from app.models import db, Category, Course, Review, User


@pytest.fixture()
def app(tmp_path):
    application = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f"sqlite:///{tmp_path / 'test.db'}",
        'WTF_CSRF_ENABLED': False,
        'AUTO_CREATE_DB': False,
        'SECRET_KEY': 'test-secret',
    })

    with application.app_context():
        db.create_all()

        category = Category(name='Программирование')
        db.session.add(category)
        db.session.flush()

        user = User(first_name='Иван', last_name='Иванов', middle_name='', login='user')
        user.set_password('qwerty')
        author = User(first_name='Пётр', last_name='Петров', middle_name='', login='author')
        author.set_password('qwerty')
        db.session.add_all([user, author])
        db.session.flush()

        course = Course(
            name='Flask для начинающих',
            short_desc='Краткое описание курса',
            full_desc='Полное описание курса',
            category_id=category.id,
            author_id=author.id,
            background_image_id=None,
        )
        db.session.add(course)
        db.session.commit()

    yield application

    with application.app_context():
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client):
    return client.post('/auth/login', data={'login': 'user', 'password': 'qwerty'}, follow_redirects=True)


def get_course_id(app):
    with app.app_context():
        return db.session.execute(db.select(Course)).scalar().id


def add_review(app, rating, text, login='user'):
    with app.app_context():
        course = db.session.execute(db.select(Course)).scalar()
        user = db.session.execute(db.select(User).filter_by(login=login)).scalar()
        review = Review(course_id=course.id, user_id=user.id, rating=rating, text=text)
        db.session.add(review)
        course.rating_sum += rating
        course.rating_num += 1
        db.session.commit()
        return review.id


def test_course_page_shows_reviews_section_and_button(client, app):
    course_id = get_course_id(app)
    response = client.get(f'/courses/{course_id}')
    assert response.status_code == 200
    assert 'Последние отзывы'.encode() in response.data
    assert 'Все отзывы'.encode() in response.data


def test_course_page_shows_last_review(client, app):
    add_review(app, 5, 'Очень полезный курс')
    course_id = get_course_id(app)
    response = client.get(f'/courses/{course_id}')
    assert response.status_code == 200
    assert 'Очень полезный курс'.encode() in response.data
    assert '5 / 5'.encode() in response.data


def test_course_page_shows_only_last_five_reviews(client, app):
    with app.app_context():
        course = db.session.execute(db.select(Course)).scalar()
        users = []
        for i in range(6):
            user = User(first_name=f'Имя{i}', last_name=f'Фамилия{i}', middle_name='', login=f'user{i}')
            user.set_password('qwerty')
            db.session.add(user)
            users.append(user)
        db.session.flush()
        for i, user in enumerate(users):
            db.session.add(Review(course_id=course.id, user_id=user.id, rating=5, text=f'Отзыв {i}'))
            course.rating_sum += 5
            course.rating_num += 1
        db.session.commit()
        course_id = course.id

    response = client.get(f'/courses/{course_id}')
    assert response.status_code == 200
    assert 'Отзыв 5'.encode() in response.data
    assert 'Отзыв 1'.encode() in response.data
    assert 'Отзыв 0'.encode() not in response.data


def test_all_reviews_page_available(client, app):
    add_review(app, 4, 'Хороший курс')
    course_id = get_course_id(app)
    response = client.get(f'/courses/{course_id}/reviews')
    assert response.status_code == 200
    assert 'Отзывы о курсе'.encode() in response.data
    assert 'Хороший курс'.encode() in response.data


def test_reviews_page_has_sort_filter(client, app):
    course_id = get_course_id(app)
    response = client.get(f'/courses/{course_id}/reviews')
    assert response.status_code == 200
    assert 'Порядок сортировки'.encode() in response.data
    assert 'По новизне'.encode() in response.data
    assert 'Сначала положительные'.encode() in response.data
    assert 'Сначала отрицательные'.encode() in response.data


def test_reviews_sort_positive(client, app):
    with app.app_context():
        course = db.session.execute(db.select(Course)).scalar()
        users = []
        for login_name in ['u1', 'u2']:
            user = User(first_name=login_name, last_name='Тест', middle_name='', login=login_name)
            user.set_password('qwerty')
            db.session.add(user)
            users.append(user)
        db.session.flush()
        db.session.add_all([
            Review(course_id=course.id, user_id=users[0].id, rating=1, text='Плохой'),
            Review(course_id=course.id, user_id=users[1].id, rating=5, text='Отличный'),
        ])
        course.rating_sum = 6
        course.rating_num = 2
        db.session.commit()
        course_id = course.id

    response = client.get(f'/courses/{course_id}/reviews?sort=positive')
    assert response.data.index('Отличный'.encode()) < response.data.index('Плохой'.encode())


def test_reviews_sort_negative(client, app):
    with app.app_context():
        course = db.session.execute(db.select(Course)).scalar()
        users = []
        for login_name in ['u3', 'u4']:
            user = User(first_name=login_name, last_name='Тест', middle_name='', login=login_name)
            user.set_password('qwerty')
            db.session.add(user)
            users.append(user)
        db.session.flush()
        db.session.add_all([
            Review(course_id=course.id, user_id=users[0].id, rating=5, text='Позитивный'),
            Review(course_id=course.id, user_id=users[1].id, rating=1, text='Негативный'),
        ])
        course.rating_sum = 6
        course.rating_num = 2
        db.session.commit()
        course_id = course.id

    response = client.get(f'/courses/{course_id}/reviews?sort=negative')
    assert response.data.index('Негативный'.encode()) < response.data.index('Позитивный'.encode())


def test_pagination_preserves_sort_parameter(client, app):
    with app.app_context():
        course = db.session.execute(db.select(Course)).scalar()
        for i in range(25):
            user = User(first_name=f'Имя{i}', last_name=f'Фамилия{i}', middle_name='', login=f'pag{i}')
            user.set_password('qwerty')
            db.session.add(user)
            db.session.flush()
            db.session.add(Review(course_id=course.id, user_id=user.id, rating=i % 6, text=f'Пагинация {i}'))
            course.rating_sum += i % 6
            course.rating_num += 1
        db.session.commit()
        course_id = course.id

    response = client.get(f'/courses/{course_id}/reviews?sort=positive')
    assert response.status_code == 200
    assert 'sort=positive'.encode() in response.data


def test_anonymous_user_sees_login_message_instead_of_review_form(client, app):
    course_id = get_course_id(app)
    response = client.get(f'/courses/{course_id}')
    assert response.status_code == 200
    assert 'Чтобы оставить отзыв'.encode() in response.data
    assert 'name="text"'.encode() not in response.data


def test_authenticated_user_sees_review_form(client, app):
    login(client)
    course_id = get_course_id(app)
    response = client.get(f'/courses/{course_id}')
    assert response.status_code == 200
    assert 'Оставить отзыв'.encode() in response.data
    assert 'name="rating"'.encode() in response.data
    assert 'name="text"'.encode() in response.data


def test_create_review_requires_authentication(client, app):
    course_id = get_course_id(app)
    response = client.post(f'/courses/{course_id}/reviews/create', data={'rating': '5', 'text': 'Текст'})
    assert response.status_code == 302
    assert '/auth/login' in response.headers['Location']


def test_authenticated_user_can_create_review(client, app):
    login(client)
    course_id = get_course_id(app)
    response = client.post(
        f'/courses/{course_id}/reviews/create',
        data={'rating': '5', 'text': 'Курс понравился'},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert 'Отзыв успешно добавлен'.encode() in response.data
    assert 'Курс понравился'.encode() in response.data

    with app.app_context():
        review = db.session.execute(db.select(Review).filter_by(text='Курс понравился')).scalar()
        course = db.session.get(Course, course_id)
        assert review is not None
        assert course.rating_sum == 5
        assert course.rating_num == 1
        assert course.rating == 5


def test_invalid_rating_highlights_field(client, app):
    login(client)
    course_id = get_course_id(app)
    response = client.post(
        f'/courses/{course_id}/reviews/create',
        data={'rating': '10', 'text': 'Текст'},
    )
    assert response.status_code == 400
    assert 'Оценка должна быть целым числом от 0 до 5'.encode() in response.data
    assert 'is-invalid'.encode() in response.data


def test_empty_review_text_highlights_field(client, app):
    login(client)
    course_id = get_course_id(app)
    response = client.post(
        f'/courses/{course_id}/reviews/create',
        data={'rating': '5', 'text': ''},
    )
    assert response.status_code == 400
    assert 'Текст отзыва не может быть пустым'.encode() in response.data
    assert 'is-invalid'.encode() in response.data


def test_user_cannot_create_second_review(client, app):
    login(client)
    course_id = get_course_id(app)
    client.post(f'/courses/{course_id}/reviews/create', data={'rating': '5', 'text': 'Первый'}, follow_redirects=True)
    response = client.post(
        f'/courses/{course_id}/reviews/create',
        data={'rating': '4', 'text': 'Второй'},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert 'Вы уже оставили отзыв к этому курсу'.encode() in response.data

    with app.app_context():
        reviews_count = db.session.execute(db.select(db.func.count(Review.id))).scalar()
        assert reviews_count == 1


def test_user_review_is_shown_instead_of_form(client, app):
    login(client)
    course_id = get_course_id(app)
    client.post(f'/courses/{course_id}/reviews/create', data={'rating': '5', 'text': 'Мой отзыв'}, follow_redirects=True)
    response = client.get(f'/courses/{course_id}')
    assert 'Ваш отзыв уже оставлен'.encode() in response.data
    assert 'Мой отзыв'.encode() in response.data
    assert 'name="text"'.encode() not in response.data
