"""
@FileName：controller.py
@Description：系统配置控制器
@Author：baojun.wang
"""
import json
from typing import Optional

from sqlalchemy.orm import Session

from app.setting.models import SystemConfig
from core.system_setting import DEFAULT_CONFIGS
from utils.custom_logging import logger


def ensure_default_configs(db: Session) -> None:
    """
    补齐内置配置项

    配置项由代码定义、页面只改值，所以缺失的行在这里按需插入，避免依赖手工初始化数据。
    """
    existing = {row.key for row in db.query(SystemConfig.key).all()}
    missing = [c for c in DEFAULT_CONFIGS if c["key"] not in existing]
    if not missing:
        return

    for conf in missing:
        db.add(SystemConfig(
            key=conf["key"],
            value=conf["value"],
            desc=conf["desc"],
            type=conf["type"],
            required=conf["required"],
        ))
    db.commit()
    logger.info(f"[系统配置] 已补齐配置项: {[c['key'] for c in missing]}")


def get_system_configs(db: Session, page_num: int = 1, page_size: int = 10) -> dict:
    """分页获取配置项列表"""
    ensure_default_configs(db)

    query = db.query(SystemConfig)
    total = query.count()
    configs = query.order_by(SystemConfig.id).offset((page_num - 1) * page_size).limit(page_size).all()
    return {"configs": [c.to_dict() for c in configs], "total": total}


def get_system_config_by_id(db: Session, config_id: int) -> Optional[SystemConfig]:
    """根据ID获取配置项"""
    return db.query(SystemConfig).filter(SystemConfig.id == config_id).first()


def validate_config_value(value: Optional[str], value_type: str, required: bool) -> Optional[str]:
    """
    校验值与类型是否匹配

    :return: 校验不通过时返回错误信息，通过返回 None
    """
    value = (value or "").strip()
    if not value:
        return "该配置项为必填项，值不能为空" if required else None

    if value_type == "NUMBER":
        try:
            float(value)
        except ValueError:
            return "值不是合法的数字"
    elif value_type == "BOOLEAN":
        if value not in ("true", "false"):
            return '布尔值只能是 "true" 或 "false"'
    elif value_type in ("DICT", "LIST"):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as e:
            return f"值不是合法的 JSON: {e}"
        if value_type == "DICT" and not isinstance(parsed, dict):
            return "值必须是 JSON 对象"
        if value_type == "LIST" and not isinstance(parsed, list):
            return "值必须是 JSON 数组"
    return None


def update_system_config(
    db: Session,
    config_id: int,
    value: Optional[str] = None,
    desc: Optional[str] = None,
    verified: Optional[bool] = None,
    update_user: str = "",
) -> bool:
    """更新配置项（键名与类型由代码定义，不可改）"""
    config = get_system_config_by_id(db, config_id)
    if not config:
        return False

    if value is not None:
        value = value.strip()
        # 地址类配置去掉末尾斜杠，避免与 REPORT_URL 拼接出 // 的路径
        if value.startswith(("http://", "https://")):
            value = value.rstrip("/")
        config.value = value
    if desc is not None:
        config.desc = desc
    if verified is not None:
        config.verified = verified
    if update_user:
        config.update_user = update_user

    db.commit()
    return True
