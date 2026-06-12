from flask import Flask
from flask_migrate import Migrate
from sqlalchemy.exc import SQLAlchemyError

from app.models import db
from app.auth import bp as auth_bp, init_login_manager
from app.courses import bp as courses_bp
from app.routes import bp as main_bp


def handle_sqlalchemy_error(err):
    error_msg = ('Возникла ошибка при подключении к базе данных. '
                 'Повторите попытку позже.')
    return f'{error_msg} (Подробнее: {err})', 500


def seed_demo_data():
    """Создаёт минимальные демонстрационные данные для локального запуска и хостинга."""
    from app.models import Category, Course, User

    if db.session.execute(db.select(Category)).first() is None:
        db.session.add_all([
            Category(name='Программирование'),
            Category(name='Математика'),
            Category(name='Языкознание'),
        ])
        db.session.commit()

    if db.session.execute(db.select(User).filter_by(login='user')).scalar() is None:
        user = User(first_name='Иван', last_name='Иванов', middle_name='', login='user')
        user.set_password('qwerty')
        db.session.add(user)
        db.session.commit()

    if db.session.execute(db.select(Course)).first() is None:
        category = db.session.execute(db.select(Category).order_by(Category.id)).scalar()
        user = db.session.execute(db.select(User).filter_by(login='user')).scalar()
        course = Course(
            name='Основы Flask',
            short_desc='Краткий вводный курс по разработке веб-приложений на Flask.',
            full_desc=('На курсе рассматриваются маршруты, шаблоны, работа с базой данных, '
                       'аутентификация пользователей и создание отзывов к курсам.'),
            category_id=category.id,
            author_id=user.id,
            background_image_id=None,
        )
        db.session.add(course)
        db.session.commit()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_pyfile('config.py')

    if test_config:
        app.config.from_mapping(test_config)

    db.init_app(app)
    Migrate(app, db)

    init_login_manager(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(courses_bp)
    app.register_blueprint(main_bp)
    app.errorhandler(SQLAlchemyError)(handle_sqlalchemy_error)

    @app.cli.command('init-demo-data')
    def init_demo_data_command():
        """Создать таблицы и демонстрационные данные."""
        db.create_all()
        seed_demo_data()
        print('Демонстрационные данные созданы.')

    if app.config.get('AUTO_CREATE_DB', True):
        with app.app_context():
            db.create_all()
            seed_demo_data()

    return app
