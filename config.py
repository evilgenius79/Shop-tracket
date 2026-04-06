import os
import secrets

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

_DEFAULT_SECRET = 'change-this-in-production-please'

class Config:
    _raw_secret = os.environ.get('SECRET_KEY', _DEFAULT_SECRET)
    if _raw_secret == _DEFAULT_SECRET:
        import sys
        print(
            '\n  WARNING: SECRET_KEY is not set. Using the insecure default.\n'
            '  Set a strong SECRET_KEY environment variable before going live:\n'
            '    export SECRET_KEY="$(python3 -c \'import secrets; print(secrets.token_hex(32))\')" \n',
            file=sys.stderr
        )
    SECRET_KEY = _raw_secret
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(BASE_DIR, 'carlot.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32MB max upload
