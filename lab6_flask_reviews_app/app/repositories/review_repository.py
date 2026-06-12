from sqlalchemy import func, desc, asc

from app.models import Review, Course, User


class ReviewRepository:
    def __init__(self, db):
        self.db = db

    def get_last_reviews_for_course(self, course_id, limit=5):
        query = (
            self.db.select(Review)
            .filter_by(course_id=course_id)
            .order_by(Review.created_at.desc(), Review.id.desc())
            .limit(limit)
        )
        return self.db.session.execute(query).scalars().all()

    def get_user_review(self, course_id, user_id):
        if not user_id:
            return None
        query = self.db.select(Review).filter_by(course_id=course_id, user_id=user_id)
        return self.db.session.execute(query).scalar()

    def get_reviews_pagination(self, course_id, sort='new'):
        query = self.db.select(Review).filter_by(course_id=course_id)

        if sort == 'positive':
            query = query.order_by(Review.rating.desc(), Review.created_at.desc(), Review.id.desc())
        elif sort == 'negative':
            query = query.order_by(Review.rating.asc(), Review.created_at.desc(), Review.id.desc())
        else:
            query = query.order_by(Review.created_at.desc(), Review.id.desc())

        return self.db.paginate(query)

    def add_review(self, course, user, rating, text):
        review = Review(
            course_id=course.id,
            user_id=user.id,
            rating=rating,
            text=text.strip(),
        )
        try:
            self.db.session.add(review)
            course.rating_sum = (course.rating_sum or 0) + rating
            course.rating_num = (course.rating_num or 0) + 1
            self.db.session.commit()
        except Exception as e:
            self.db.session.rollback()
            raise e
        return review

    def recount_course_rating(self, course):
        totals = self.db.session.execute(
            self.db.select(
                func.coalesce(func.sum(Review.rating), 0),
                func.count(Review.id),
            ).filter_by(course_id=course.id)
        ).one()
        course.rating_sum = totals[0]
        course.rating_num = totals[1]
        self.db.session.commit()
        return course
