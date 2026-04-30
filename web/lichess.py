from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from core.database import SyncSessionFactory
from models import ChessUser
import berserk

lichess_bp = Blueprint("lichess", __name__)


def _verify_lichess(username: str, token: str) -> tuple[bool, str]:
    try:
        client = berserk.Client(berserk.TokenSession(token))
        account = client.account.get()
    except berserk.exceptions.ResponseError as e:
        if e.status_code == 401:
            return False, "Token 无效或已过期"
        return False, f"Lichess 返回异常: {e.status_code}"
    except Exception:
        return False, "无法连接 Lichess 服务"

    real_username = account.get("username", "")
    if real_username.lower() != username.lower():
        return False, f"Token 对应的用户名是 {real_username}，与输入不一致"

    return True, ""


@lichess_bp.route("/lichess/bind", methods=["GET", "POST"])
@login_required
def bind_lichess():
    lichess_info = None
    try:
        with SyncSessionFactory() as session:
            existing = session.query(ChessUser).filter_by(
                userId=current_user.id, battlePlatform="lichess"
            ).first()

            if existing:
                lichess_info = {
                    "lichess_username": existing.userName,
                    "token": existing.token,
                }

            if request.method == "POST":
                lichess_name = request.form.get("lichess_username", "").strip()
                lichess_token = request.form.get("lichess_token", "").strip()
                if not lichess_name or not lichess_token:
                    flash("Lichess 用户名和 Token 不能为空")
                else:
                    ok, err = _verify_lichess(lichess_name, lichess_token)
                    if not ok:
                        flash(err)
                    elif existing:
                        existing.userName = lichess_name
                        existing.token = lichess_token
                        session.commit()
                        flash("Lichess 账号已更新")
                        return redirect(url_for("auth.dashboard"))
                    else:
                        session.add(ChessUser(
                            userId=current_user.id,
                            userName=lichess_name,
                            token=lichess_token,
                            battlePlatform="lichess",
                        ))
                        session.commit()
                        flash("Lichess 账号绑定成功")
                        return redirect(url_for("auth.dashboard"))
    except Exception:
        flash("服务器内部错误，请稍后重试")

    return render_template("bind_lichess.html", lichess_info=lichess_info)
