from flask_login import LoginManager, UserMixin, current_user
from flask import Flask, abort
from functools import wraps
from config import Config
import logging

login_manager = LoginManager()


class LoginUser(UserMixin):
    def __init__(self, user, role="user"):
        self.raw_id = user.id
        self.id = f"a_{self.raw_id}" if role == "admin" else f"u_{self.raw_id}"
        self.username = user.userName
        self.role = role


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if current_user.role != "admin":
            abort(403)
        return f(*args, **kwargs)
    return decorated


def superadmin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if current_user.username != "admin":
            abort(403)
        return f(*args, **kwargs)
    return decorated


@login_manager.user_loader
def load_user(user_id):
    from core.database import SyncSessionFactory
    from models import User, Admin
    if user_id.startswith("a_"):
        raw_id = int(user_id[2:])
        with SyncSessionFactory() as session:
            admin = session.get(Admin, raw_id)
            if admin:
                return LoginUser(admin, role="admin")
    elif user_id.startswith("u_"):
        raw_id = int(user_id[2:])
        with SyncSessionFactory() as session:
            user = session.get(User, raw_id)
            if user:
                return LoginUser(user, role="user")
    return None


def create_app():
    app = Flask(__name__)
    app.secret_key = Config.SECRET_KEY

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    werkzeug_logger = logging.getLogger("werkzeug")
    web_logger = logging.getLogger("AlphaGames.web")
    for h in web_logger.handlers:
        werkzeug_logger.addHandler(h)
    werkzeug_logger.setLevel(web_logger.level)

    from web.auth import auth_bp
    from web.device import device_bp
    from web.lichess import lichess_bp
    from web.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(device_bp)
    app.register_blueprint(lichess_bp)
    app.register_blueprint(admin_bp)

    return app
