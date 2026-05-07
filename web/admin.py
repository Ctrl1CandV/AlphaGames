from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from core.database import SyncSessionFactory
from models import User, Admin, Device, ChessUser, ChessRecord
from sqlalchemy import func
from web import admin_required, superadmin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@admin_required
def index():
    try:
        with SyncSessionFactory() as session:
            user_count = session.query(func.count(User.id)).scalar()
            device_count = session.query(func.count(Device.id)).scalar()
            lichess_count = session.query(func.count(ChessUser.id)).scalar()
            record_count = session.query(func.count(ChessRecord.id)).scalar()
    except Exception:
        flash("无法加载统计数据", "error")
        user_count = device_count = lichess_count = record_count = 0

    return render_template("admin/index.html",
                           user_count=user_count,
                           device_count=device_count,
                           lichess_count=lichess_count,
                           record_count=record_count)


@admin_bp.route("/users")
@admin_required
def list_users():
    try:
        with SyncSessionFactory() as session:
            users = session.query(User).order_by(User.id).all()
    except Exception:
        flash("无法加载用户列表", "error")
        users = []
    return render_template("admin/users.html", users=users)


@admin_bp.route("/users/<int:user_id>")
@admin_required
def user_detail(user_id):
    try:
        with SyncSessionFactory() as session:
            user = session.get(User, user_id)
            if not user:
                flash("用户不存在", "error")
                return redirect(url_for("admin.list_users"))
            device = session.query(Device).filter_by(userName=user.userName).first()
            lichess = session.query(ChessUser).filter_by(userId=user.id).first()
            records = session.query(ChessRecord).filter_by(
                userName=user.userName
            ).order_by(ChessRecord.id.desc()).limit(20).all()
    except Exception:
        flash("无法加载用户详情", "error")
        return redirect(url_for("admin.list_users"))

    return render_template("admin/user_detail.html",
                           user=user, device=device,
                           lichess=lichess, records=records)


@admin_bp.route("/create-admin", methods=["POST"])
@superadmin_required
def create_admin():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if not username or not password:
        flash("用户名和密码不能为空", "error")
    elif len(password) < 4:
        flash("密码长度至少4位", "error")
    else:
        try:
            with SyncSessionFactory() as session:
                if session.query(Admin).filter_by(userName=username).first() or \
                   session.query(User).filter_by(userName=username).first():
                    flash("用户名已存在", "error")
                else:
                    session.add(Admin(
                        userName=username,
                        password=generate_password_hash(password),
                    ))
                    session.commit()
                    flash(f"已创建管理员: {username}", "success")
        except Exception:
            flash("操作失败", "error")
    return redirect(url_for("admin.index"))


@admin_bp.route("/records")
@admin_required
def list_records():
    try:
        with SyncSessionFactory() as session:
            records = session.query(ChessRecord).order_by(
                ChessRecord.id.desc()
            ).limit(50).all()
    except Exception:
        flash("无法加载棋谱列表", "error")
        records = []
    return render_template("admin/records.html", records=records)
