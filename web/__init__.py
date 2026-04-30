from flask import Flask
from flask_login import LoginManager, UserMixin
from config import Config

login_manager = LoginManager()


class LoginUser(UserMixin):
    """Flask-Login 适配器，包装 SQLAlchemy User 模型"""

    def __init__(self, user):
        self.id = str(user.id)
        self.username = user.userName


@login_manager.user_loader
def load_user(user_id):
    from core.database import SyncSessionFactory
    from models import User
    with SyncSessionFactory() as session:
        user = session.get(User, int(user_id))
        if user:
            return LoginUser(user)
    return None


def create_app():
    app = Flask(__name__)
    app.secret_key = Config.SECRET_KEY

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    from web.auth import auth_bp
    from web.device import device_bp
    from web.lichess import lichess_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(device_bp)
    app.register_blueprint(lichess_bp)

    return app
