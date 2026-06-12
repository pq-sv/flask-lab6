from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from app.models import db
from app.repositories import (
    CourseRepository,
    UserRepository,
    CategoryRepository,
    ImageRepository,
    ReviewRepository,
)

user_repository = UserRepository(db)
course_repository = CourseRepository(db)
category_repository = CategoryRepository(db)
image_repository = ImageRepository(db)
review_repository = ReviewRepository(db)

bp = Blueprint('courses', __name__, url_prefix='/courses')

COURSE_PARAMS = [
    'author_id', 'name', 'category_id', 'short_desc', 'full_desc'
]

SORT_OPTIONS = {
    'new': 'По новизне',
    'positive': 'Сначала положительные',
    'negative': 'Сначала отрицательные',
}

RATING_OPTIONS = [
    (5, 'отлично'),
    (4, 'хорошо'),
    (3, 'удовлетворительно'),
    (2, 'неудовлетворительно'),
    (1, 'плохо'),
    (0, 'ужасно'),
]


def params():
    return {p: request.form.get(p) or None for p in COURSE_PARAMS}


def search_params():
    return {
        'name': request.args.get('name'),
        'category_ids': [x for x in request.args.getlist('category_ids') if x],
    }


def review_form_context(course_id):
    user_review = None
    if current_user.is_authenticated:
        user_review = review_repository.get_user_review(course_id, current_user.id)
    return {
        'rating_options': RATING_OPTIONS,
        'user_review': user_review,
    }


def validate_review_form():
    errors = {}
    rating_raw = request.form.get('rating')
    text = (request.form.get('text') or '').strip()

    try:
        rating = int(rating_raw)
    except (TypeError, ValueError):
        rating = None

    if rating is None or rating < 0 or rating > 5:
        errors['rating'] = 'Оценка должна быть целым числом от 0 до 5.'

    if not text:
        errors['text'] = 'Текст отзыва не может быть пустым.'

    return errors, rating, text


@bp.route('/')
def index():
    pagination = course_repository.get_pagination_info(**search_params())
    courses = course_repository.get_all_courses(pagination=pagination)
    categories = category_repository.get_all_categories()
    return render_template('courses/index.html',
                           courses=courses,
                           categories=categories,
                           pagination=pagination,
                           search_params=search_params())


@bp.route('/new')
@login_required
def new():
    course = course_repository.new_course()
    categories = category_repository.get_all_categories()
    users = user_repository.get_all_users()
    return render_template('courses/new.html',
                           categories=categories,
                           users=users,
                           course=course)


@bp.route('/create', methods=['POST'])
@login_required
def create():
    f = request.files.get('background_img')
    img = None
    course = None

    try:
        if f and f.filename:
            img = image_repository.add_image(f)

        image_id = img.id if img else None
        course = course_repository.add_course(**params(), background_image_id=image_id)
    except IntegrityError as err:
        flash(f'Возникла ошибка при записи данных в БД. Проверьте корректность введённых данных. ({err})', 'danger')
        categories = category_repository.get_all_categories()
        users = user_repository.get_all_users()
        return render_template('courses/new.html',
                               categories=categories,
                               users=users,
                               course=course or course_repository.new_course())

    flash(f'Курс {course.name} был успешно добавлен!', 'success')

    return redirect(url_for('courses.index'))


@bp.route('/<int:course_id>')
def show(course_id):
    course = course_repository.get_course_by_id(course_id)
    if course is None:
        abort(404)

    last_reviews = review_repository.get_last_reviews_for_course(course_id, limit=5)
    return render_template(
        'courses/show.html',
        course=course,
        last_reviews=last_reviews,
        review_errors={},
        review_form=request.form,
        **review_form_context(course_id),
    )


@bp.route('/<int:course_id>/reviews')
def reviews(course_id):
    course = course_repository.get_course_by_id(course_id)
    if course is None:
        abort(404)

    sort = request.args.get('sort', 'new')
    if sort not in SORT_OPTIONS:
        sort = 'new'

    pagination = review_repository.get_reviews_pagination(course_id, sort=sort)

    return render_template(
        'courses/reviews.html',
        course=course,
        reviews=pagination.items,
        pagination=pagination,
        sort=sort,
        sort_options=SORT_OPTIONS,
        review_errors={},
        review_form=request.form,
        **review_form_context(course_id),
    )


@bp.route('/<int:course_id>/reviews/create', methods=['POST'])
@login_required
def create_review(course_id):
    course = course_repository.get_course_by_id(course_id)
    if course is None:
        abort(404)

    if review_repository.get_user_review(course_id, current_user.id):
        flash('Вы уже оставили отзыв к этому курсу.', 'warning')
        return redirect(request.referrer or url_for('courses.show', course_id=course_id))

    errors, rating, text = validate_review_form()
    if errors:
        flash('Проверьте корректность заполнения формы отзыва.', 'danger')
        last_reviews = review_repository.get_last_reviews_for_course(course_id, limit=5)
        sort = request.args.get('sort', 'new')
        if request.referrer and '/reviews' in request.referrer:
            pagination = review_repository.get_reviews_pagination(course_id, sort=sort if sort in SORT_OPTIONS else 'new')
            return render_template(
                'courses/reviews.html',
                course=course,
                reviews=pagination.items,
                pagination=pagination,
                sort=sort if sort in SORT_OPTIONS else 'new',
                sort_options=SORT_OPTIONS,
                review_errors=errors,
                review_form=request.form,
                **review_form_context(course_id),
            ), 400
        return render_template(
            'courses/show.html',
            course=course,
            last_reviews=last_reviews,
            review_errors=errors,
            review_form=request.form,
            **review_form_context(course_id),
        ), 400

    try:
        review_repository.add_review(course, current_user, rating, text)
    except IntegrityError:
        flash('Вы уже оставили отзыв к этому курсу.', 'warning')
        return redirect(url_for('courses.show', course_id=course_id))

    flash('Отзыв успешно добавлен.', 'success')
    return redirect(request.referrer or url_for('courses.show', course_id=course_id))
