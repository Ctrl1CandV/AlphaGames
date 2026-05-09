from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from core.database import SyncSessionFactory
from models import GameConfig

game_config_bp = Blueprint("game_config", __name__)


@game_config_bp.route("/game/config", methods=["GET", "POST"])
@login_required
def config():
    with SyncSessionFactory() as session:
        cfg = session.query(GameConfig).filter_by(
            userName=current_user.username
        ).first()

        if request.method == "POST":
            engine_color = request.form.get("engineColor", "random")
            if engine_color not in ("white", "black", "random"):
                engine_color = "random"
            ai_level = int(request.form.get("aiLevel", "3"))
            ai_level = max(1, min(8, ai_level))
            time_val = int(request.form.get("time", "10"))
            time_val = max(1, min(180, time_val))
            increment = int(request.form.get("increment", "5"))
            increment = max(0, min(60, increment))

            if cfg:
                cfg.engineColor = engine_color
                cfg.aiLevel = ai_level
                cfg.time = time_val
                cfg.increment = increment
            else:
                session.add(GameConfig(
                    userName=current_user.username,
                    engineColor=engine_color,
                    aiLevel=ai_level,
                    time=time_val,
                    increment=increment,
                ))
            session.commit()
            flash("对局配置已保存", "success")
            return redirect(url_for("game_config.config"))

    return render_template("game_config.html", config=cfg)
