import os

SECRET_KEY = os.getenv('SECRET_KEY', 'secret-key')

SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///project.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ECHO = False
AUTO_CREATE_DB = os.getenv('AUTO_CREATE_DB', '1') == '1'

UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..',
    'media',
    'images'
)
