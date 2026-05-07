from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from core.database import SyncSessionFactory
from models import User, Admin, Device, ChessUser, ChessUploadMode
from web import LoginUser

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    login_type = request.args.get("role", "user")
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        try:
            with SyncSessionFactory() as session:
                if login_type == "admin":
                    admin = session.query(Admin).filter_by(userName=username).first()
                    if not admin:
                        flash("该账号不是管理员账号", "error")
                    elif not check_password_hash(admin.password, password):
                        flash("用户名或密码错误", "error")
                    else:
                        login_user(LoginUser(admin, role="admin"))
                        return redirect(url_for("admin.index"))
                else:
                    if session.query(Admin).filter_by(userName=username).first():
                        flash("管理员请使用管理员入口登录", "error")
                    else:
                        user = session.query(User).filter_by(userName=username).first()
                        if not user or not check_password_hash(user.password, password):
                            flash("用户名或密码错误", "error")
                        else:
                            login_user(LoginUser(user, role="user"))
                            return redirect(url_for("auth.dashboard"))
        except Exception:
            flash("服务器内部错误，请稍后重试", "error")
    return render_template("login.html", login_type=login_type)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not username or not password:
            flash("用户名和密码不能为空", "error")
        elif password != confirm:
            flash("两次输入的密码不一致", "error")
        else:
            try:
                with SyncSessionFactory() as session:
                    if session.query(User).filter_by(userName=username).first():
                        flash("用户名已存在", "error")
                    else:
                        session.add(User(
                            userName=username,
                            password=generate_password_hash(password),
                        ))
                        session.commit()
                        flash("注册成功，请登录", "success")
                        return redirect(url_for("auth.login"))
            except Exception:
                flash("服务器内部错误，请稍后重试", "error")
    return render_template("register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/dashboard")
@login_required
def dashboard():
    device = None
    lichess_info = None
    upload_mode = 0
    try:
        with SyncSessionFactory() as session:
            device = session.query(Device).filter_by(
                userName=current_user.username
            ).first()
            lichess_record = session.query(ChessUser).filter_by(
                userId=current_user.raw_id, battlePlatform="lichess"
            ).first()
            if lichess_record:
                lichess_info = {
                    "lichess_username": lichess_record.userName,
                }
            mode_record = session.query(ChessUploadMode).filter_by(
                userName=current_user.username
            ).first()
            if mode_record:
                upload_mode = mode_record.uploadMode
    except Exception:
        flash("无法加载面板数据，请稍后重试", "error")
    return render_template("dashboard.html",
                           device=device, lichess_info=lichess_info,
                           upload_mode=upload_mode)
