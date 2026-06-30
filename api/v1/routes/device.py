"""
设备管理相关路由
"""
from fastapi import APIRouter, Depends
from core.response import api_response
from core.auth_middleware import get_current_user
from app.user.models import UserModel
from app.device.devices_models import AndroidDevice
from core.database import get_sync_db
import subprocess
import re
from pathlib import Path
import uuid
from datetime import datetime

router = APIRouter(prefix="/device", tags=["设备管理"])


def get_device_info(device_id):
    """获取设备详细信息"""
    info = {
        "id": device_id,
        "android_id": None,
        "brand": "Unknown",
        "model": "Unknown",
        "resolution": "Unknown",
        "android_version": "Unknown",
        "system_type": "android",
        "status": "disconnected"
    }
    
    try:
        # 检查设备是否在线
        check_cmd = ["adb", "-s", device_id, "shell", "getprop", "ro.build.version.release"]
        result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return info
        
        info["status"] = "connected"

        # 获取 android_id
        android_id_cmd = ["adb", "-s", device_id, "shell", "settings", "get", "secure", "android_id"]
        android_id_result = subprocess.run(android_id_cmd, capture_output=True, text=True, timeout=5)
        if android_id_result.returncode == 0:
            android_id = android_id_result.stdout.strip()
            if android_id:
                info["android_id"] = android_id

        # 获取品牌
        brand_cmd = ["adb", "-s", device_id, "shell", "getprop", "ro.product.brand"]
        brand_result = subprocess.run(brand_cmd, capture_output=True, text=True, timeout=5)
        if brand_result.returncode == 0:
            info["brand"] = brand_result.stdout.strip().capitalize()
        
        # 获取型号
        model_cmd = ["adb", "-s", device_id, "shell", "getprop", "ro.product.model"]
        model_result = subprocess.run(model_cmd, capture_output=True, text=True, timeout=5)
        if model_result.returncode == 0:
            info["model"] = model_result.stdout.strip()
        
        # 获取设置的分辨率（优先取Override size，如果没有则取Physical size）
        wm_cmd = ["adb", "-s", device_id, "shell", "wm", "size"]
        wm_result = subprocess.run(wm_cmd, capture_output=True, text=True, timeout=5)
        if wm_result.returncode == 0:
            # 优先匹配 Override size（设置的分辨率）
            override_match = re.search(r'Override size:\s*(\d+)x(\d+)', wm_result.stdout)
            if override_match:
                info["resolution"] = f"{override_match.group(1)}x{override_match.group(2)}"
            else:
                # 如果没有Override，匹配Physical size（物理分辨率）
                physical_match = re.search(r'Physical size:\s*(\d+)x(\d+)', wm_result.stdout)
                if physical_match:
                    info["resolution"] = f"{physical_match.group(1)}x{physical_match.group(2)}"
        
        # 获取系统版本
        # 华为和荣耀设备优先获取Harmony版本
        brand_lower = info["brand"].lower()
        if brand_lower in ["huawei", "honor"]:
            harmony_cmd = ["adb", "-s", device_id, "shell", "getprop", "hw_sc.build.platform.version"]
            harmony_result = subprocess.run(harmony_cmd, capture_output=True, text=True, timeout=5)
            if harmony_result.returncode == 0:
                harmony_version = harmony_result.stdout.strip()
                if harmony_version and harmony_version != "Unknown":
                    info["android_version"] = f"HarmonyOS {harmony_version}"
                    info["system_type"] = "harmonyos"
        
        # 如果不是Harmony或获取失败，使用Android版本
        if info["system_type"] == "android":
            info["android_version"] = result.stdout.strip()
        
    except Exception as e:
        print(f"获取设备信息失败: {e}")
    
    return info


def update_device_in_db(device_info):
    """更新设备信息到数据库"""
    try:
        for session in get_sync_db():
            # 查找或创建设备记录
            device = session.query(AndroidDevice).filter(AndroidDevice.id == device_info["id"]).first()

            if device:
                # 更新现有设备
                device.brand = device_info["brand"]
                device.model = device_info["model"]
                device.resolution = device_info["resolution"]
                device.android_version = device_info["android_version"]
                device.system_type = device_info["system_type"]
                device.status = device_info["status"]
                # 只有当获取到新的android_id时才更新（避免覆盖已有的）
                if "android_id" in device_info and device_info["android_id"]:
                    device.android_id = device_info["android_id"]
                if device_info["status"] == "connected":
                    device.last_connected_at = datetime.now()
            else:
                # 创建新设备记录
                new_device = AndroidDevice(
                    id=device_info["id"],
                    android_id=device_info.get("android_id"),
                    brand=device_info["brand"],
                    model=device_info["model"],
                    resolution=device_info["resolution"],
                    android_version=device_info["android_version"],
                    system_type=device_info["system_type"],
                    status=device_info["status"],
                    last_connected_at=datetime.now() if device_info["status"] == "connected" else None
                )
                session.add(new_device)
            session.commit()
    except Exception as e:
        print(f"更新设备数据库失败: {e}")


def find_device_by_android_id(android_id):
    """通过android_id查找设备"""
    for session in get_sync_db():
        device = session.query(AndroidDevice).filter(AndroidDevice.android_id == android_id, AndroidDevice.is_deleted == 0).first()
        if device:
            return {
                "id": device.id,
                "android_id": device.android_id,
                "brand": device.brand,
                "model": device.model,
                "resolution": device.resolution,
                "android_version": device.android_version,
                "system_type": device.system_type,
                "status": device.status,
                "last_connected_at": device.last_connected_at.isoformat() if device.last_connected_at else None,
                "created_at": device.created_at.isoformat() if device.created_at else None
            }
    return None


@router.get("/list")
async def list_devices(
    search: str = None,
    current_user: UserModel = Depends(get_current_user)
):
    """获取设备列表（包含已连接和历史设备），支持搜索和在线设备过滤"""
    devices = []
    search_keyword = search.lower() if search else None
    
    try:
        # 获取当前连接的设备ID集合
        connected_device_ids = set()
        offline_device_ids = set()
        
        try:
            result = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True, timeout=10)
            lines = result.stdout.strip().split('\n')[1:]
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    device_id = parts[0]
                    status = parts[1]
                    if status == 'device':
                        connected_device_ids.add(device_id)
                    elif status == 'offline':
                        offline_device_ids.add(device_id)
        except Exception as e:
            print(f"获取ADB设备列表失败: {e}")
        
        # 从数据库获取所有设备
        for session in get_sync_db():
            db_devices = session.query(AndroidDevice).filter(AndroidDevice.is_deleted == 0).all()
            
            for db_device in db_devices:
                device_dict = {
                    "id": db_device.id,
                    "android_id": db_device.android_id,
                    "brand": db_device.brand,
                    "model": db_device.model,
                    "resolution": db_device.resolution,
                    "android_version": db_device.android_version,
                    "system_type": db_device.system_type,
                    "status": db_device.status,
                    "last_connected_at": db_device.last_connected_at.isoformat() if db_device.last_connected_at else None,
                    "created_at": db_device.created_at.isoformat() if db_device.created_at else None
                }
                
                # 更新在线状态
                if db_device.id in connected_device_ids:
                    # 在线设备，获取最新信息
                    device_info = get_device_info(db_device.id)
                    if device_info["brand"] != "Unknown":
                        # 成功获取到设备信息，才更新数据库
                        device_info["status"] = "connected"
                        update_device_in_db(device_info)
                        device_dict.update(device_info)
                    else:
                        # 获取失败，保持数据库中的信息，只更新状态
                        device_dict["status"] = "connected"
                elif db_device.id in offline_device_ids:
                    device_dict["status"] = "offline"
                    update_device_in_db({"id": db_device.id, "status": "offline", "brand": db_device.brand,
                                        "model": db_device.model, "resolution": db_device.resolution,
                                        "android_version": db_device.android_version, "system_type": db_device.system_type})
                else:
                    device_dict["status"] = "disconnected"
                    update_device_in_db({"id": db_device.id, "status": "disconnected", "brand": db_device.brand,
                                        "model": db_device.model, "resolution": db_device.resolution,
                                        "android_version": db_device.android_version, "system_type": db_device.system_type})
                
                devices.append(device_dict)
        
        # 处理新连接的设备（数据库中不存在的）
        for device_id in connected_device_ids:
            device_exists = any(d["id"] == device_id for d in devices)
            if not device_exists:
                device_info = get_device_info(device_id)
                device_info["status"] = "connected"
                update_device_in_db(device_info)
                devices.append(device_info)
    
    except Exception as e:
        print(f"获取设备列表失败: {e}")
    
    # 过滤：只返回在线设备
    devices = [d for d in devices if d['status'] == 'connected']
    
    # 设备去重：同一个设备既连接了有线还连接了无线adb，都在线时，只返回有线的
    # 有线设备通常是没有冒号的，无线设备通常是ip:port格式（有冒号）
    seen_android_id = {}  # key: android_id, value: device
    no_android_id_devices = []  # 没有android_id的设备

    for d in devices:
        android_id = d.get('android_id')
        if not android_id:
            no_android_id_devices.append(d)
            continue
        # 判断是否是有线设备（没有冒号）
        is_wired = ':' not in d['id']
        # 如果android_id还没记录，或者当前是有线设备（有线设备优先级更高）
        if android_id not in seen_android_id or is_wired:
            seen_android_id[android_id] = d

    # 重新构建去重后的设备列表
    devices = list(seen_android_id.values()) + no_android_id_devices
    
    # 搜索过滤
    if search_keyword:
        devices = [
            d for d in devices
            if search_keyword in d.get('brand', '').lower()
            or search_keyword in d.get('model', '').lower()
            or search_keyword in d.get('id', '').lower()
        ]
    
    return api_response(data=devices)


@router.get("/screenshot/{device_id}")
async def get_device_screenshot(
    device_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """获取设备截图"""
    try:
        # 创建临时目录存储截图
        screenshot_dir = Path("temp/screenshots")
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成唯一文件名
        filename = f"screenshot_{device_id.replace(':', '_')}_{uuid.uuid4().hex}.png"
        local_path = screenshot_dir / filename
        
        # 截图并拉取
        subprocess.run(
            ["adb", "-s", device_id, "shell", "screencap", "-p", "/sdcard/screenshot.png"],
            capture_output=True,
            timeout=30
        )
        subprocess.run(
            ["adb", "-s", device_id, "pull", "/sdcard/screenshot.png", str(local_path)],
            capture_output=True,
            timeout=30
        )
        
        # 删除设备上的临时文件
        subprocess.run(
            ["adb", "-s", device_id, "shell", "rm", "/sdcard/screenshot.png"],
            capture_output=True,
            timeout=5
        )
        
        if local_path.exists():
            from fastapi.responses import FileResponse
            return FileResponse(
                path=str(local_path),
                media_type="image/png",
                filename=filename
            )
        
        return api_response(code=1, message="截图生成失败")
    
    except Exception as e:
        print(f"获取截图失败: {e}")
        return api_response(code=1, message=f"获取截图失败: {str(e)}")


@router.post("/refresh/{device_id}")
async def refresh_device(
    device_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """刷新设备信息"""
    device_info = get_device_info(device_id)
    
    # 只有当设备成功连接并获取到真实信息时才更新数据库
    # 如果设备离线（返回的是默认Unknown值），保持数据库中的原有信息不变
    if device_info["brand"] != "Unknown":
        update_device_in_db(device_info)
        return api_response(data=device_info)
    else:
        # 设备离线，从数据库获取原有信息
        for session in get_sync_db():
            device = session.query(AndroidDevice).filter(AndroidDevice.id == device_id, AndroidDevice.is_deleted == 0).first()
            if device:
                device_info = {
                    "id": device.id,
                    "android_id": device.android_id,
                    "brand": device.brand,
                    "model": device.model,
                    "resolution": device.resolution,
                    "android_version": device.android_version,
                    "system_type": device.system_type,
                    "status": "offline"
                }
        return api_response(data=device_info)


@router.get("/find-by-android-id")
async def find_device_by_android_id_api(
    android_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """通过android_id查找设备"""
    device = find_device_by_android_id(android_id)
    if device:
        return api_response(data=device)
    else:
        return api_response(code=1, message="未找到匹配的设备")


@router.get("/match-device")
async def match_device(
    device_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """
    设备匹配：当设备断连时，尝试通过android_id查找相同设备的其他连接方式
    如果原始设备ID（有线连接）断连，尝试查找具有相同android_id的在线设备
    """
    try:
        # 先检查当前设备是否在线
        result = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True, timeout=10)
        lines = result.stdout.strip().split('\n')[1:]
        connected_device_ids = set()

        for line in lines:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[1] == 'device':
                connected_device_ids.add(parts[0])

        # 如果设备在线，直接返回
        if device_id in connected_device_ids:
            device_info = get_device_info(device_id)
            return api_response(data={"matched_device_id": device_id, "device_info": device_info, "matched": True})

        # 设备不在线，尝试通过android_id查找
        # 先从数据库获取该设备的android_id
        for session in get_sync_db():
            device = session.query(AndroidDevice).filter(AndroidDevice.id == device_id, AndroidDevice.is_deleted == 0).first()
            if device and device.android_id:
                # 查找具有相同android_id的其他在线设备
                online_devices = session.query(AndroidDevice).filter(
                    AndroidDevice.android_id == device.android_id,
                    AndroidDevice.id != device_id,
                    AndroidDevice.status == "connected",
                    AndroidDevice.is_deleted == 0
                ).all()

                for online_device in online_devices:
                    if online_device.id in connected_device_ids:
                        device_info = get_device_info(online_device.id)
                        return api_response(data={
                            "matched_device_id": online_device.id,
                            "device_info": device_info,
                            "matched": True,
                            "original_device_id": device_id,
                            "message": f"设备 {device_id} 已断连，已自动切换到同一设备的无线连接 {online_device.id}"
                        })

        return api_response(data={
            "matched_device_id": None,
            "matched": False,
            "message": f"设备 {device_id} 当前不在线，且未找到相同android_id的在线设备"
        })

    except Exception as e:
        print(f"设备匹配失败: {e}")
        return api_response(code=1, message=f"设备匹配失败: {str(e)}")


@router.delete("/{device_id}")
async def delete_device(
    device_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """删除设备记录"""
    try:
        for session in get_sync_db():
            device = session.query(AndroidDevice).filter(AndroidDevice.id == device_id).first()
            if device:
                device.is_deleted = 1
                session.commit()
                return api_response(message="设备已删除")
            else:
                return api_response(code=1, message="设备不存在")
    except Exception as e:
        print(f"删除设备失败: {e}")
        return api_response(code=1, message=f"删除设备失败: {str(e)}")
