from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from core.database import SyncSessionFactory
from models import Device

device_bp = Blueprint("device", __name__)


@device_bp.route("/device/bind", methods=["GET", "POST"])
@login_required
def bind_device():
    mine = None
    try:
        with SyncSessionFactory() as session:
            mine = session.query(Device).filter_by(
                userName=current_user.username
            ).first()

            if request.method == "POST":
                sn = request.form.get("sn", "").strip()
                if not sn:
                    flash("SN码不能为空")
                else:
                    conflict = session.query(Device).filter(
                        Device.sn == sn, Device.userName != current_user.username
                    ).first()
                    if conflict:
                        flash("该棋盘已被其他用户绑定")
                    elif mine:
                        mine.sn = sn
                        session.commit()
                        flash("棋盘已更新")
                        return redirect(url_for("auth.dashboard"))
                    else:
                        session.add(Device(
                            userName=current_user.username, sn=sn
                        ))
                        session.commit()
                        flash("棋盘绑定成功")
                        return redirect(url_for("auth.dashboard"))
    except Exception:
        flash("服务器内部错误，请稍后重试")

    return render_template("bind_device.html", device=mine)
