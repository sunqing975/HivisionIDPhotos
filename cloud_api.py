# -*- coding: utf-8 -*-
"""
微信云托管 callContainer JSON 兼容端点
-------------------------------------
小程序 wx.cloud.callContainer 只能发送 JSON body，而 FastAPI 的 Form 参数
只接受表单编码（application/x-www-form-urlencoded / multipart），直接传 JSON
会返回 405。本文件新增 /api/idphoto、/api/add_background 两个 JSON 端点，
处理逻辑与 deploy_api.py 完全一致，供小程序 callContainer 调用。

复用 deploy_api 中已创建的 IDCreator 实例（不重复加载模型，避免内存翻倍）。
"""
from fastapi import APIRouter, Body

from deploy_api import creator
from hivision.error import FaceError
from hivision.creator.choose_handler import choose_handler
from hivision.utils import (
    add_background,
    resize_image_to_kb,
    bytes_2_base64,
    base64_2_numpy,
    hex_to_rgb,
    save_image_dpi_to_bytes,
)
import numpy as np
import cv2

router = APIRouter()


def _load_img(body: dict, convert_rgb: bool = False):
    """从 JSON body 提取 input_image_base64 并解码，缺失返回 None。

    convert_rgb=True：idphoto 用（官方 base64 路径未做 BGR→RGB，导致人脸检测失败；
    与 multipart 路径保持一致）；add_background 需要保留 alpha 通道，不转。
    """
    b64 = body.get("input_image_base64")
    if not b64:
        return None
    img = base64_2_numpy(b64)
    if convert_rgb:
        if img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        elif img.shape[2] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        elif img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
    return img


@router.post("/api/idphoto")
async def api_idphoto(body: dict = Body(...)):
    img = _load_img(body, convert_rgb=True)
    if img is None:
        return {"status": False, "message": "missing input_image_base64"}

    choose_handler(
        creator,
        body.get("human_matting_model", "modnet_photographic_portrait_matting"),
        body.get("face_detect_model", "mtcnn"),
    )

    size = (int(body.get("height", 413)), int(body.get("width", 295)))
    try:
        result = creator(
            img,
            size=size,
            head_measure_ratio=float(body.get("head_measure_ratio", 0.2)),
            head_height_ratio=float(body.get("head_height_ratio", 0.45)),
            head_top_range=(
                float(body.get("top_distance_max", 0.12)),
                float(body.get("top_distance_min", 0.10)),
            ),
            face_alignment=bool(body.get("face_align", False)),
            whitening_strength=int(body.get("whitening_strength", 0)),
            brightness_strength=int(body.get("brightness_strength", 0)),
            contrast_strength=int(body.get("contrast_strength", 0)),
            sharpen_strength=int(body.get("sharpen_strength", 0)),
            saturation_strength=int(body.get("saturation_strength", 0)),
        )
    except FaceError:
        return {"status": False}

    dpi = int(body.get("dpi", 300))
    result_message = {
        "status": True,
        "image_base64_standard": bytes_2_base64(
            save_image_dpi_to_bytes(result.standard, None, dpi)
        ),
    }
    if body.get("hd", True):
        result_message["image_base64_hd"] = bytes_2_base64(
            save_image_dpi_to_bytes(result.hd, None, dpi)
        )
    return result_message


@router.post("/api/add_background")
async def api_add_background(body: dict = Body(...)):
    img = _load_img(body)
    if img is None:
        return {"status": False, "message": "missing input_image_base64"}

    render_choice = ["pure_color", "updown_gradient", "center_gradient"]
    color = hex_to_rgb(body.get("color", "000000"))
    color = (color[2], color[1], color[0])

    result_image = add_background(
        img,
        bgr=color,
        mode=render_choice[int(body.get("render", 0))],
    ).astype(np.uint8)

    result_image = cv2.cvtColor(result_image, cv2.COLOR_RGB2BGR)

    kb = body.get("kb")
    dpi = int(body.get("dpi", 300))
    if kb:
        result_image_bytes = resize_image_to_kb(result_image, None, int(kb), dpi=dpi)
    else:
        result_image_bytes = save_image_dpi_to_bytes(result_image, None, dpi=dpi)

    return {"status": True, "image_base64": bytes_2_base64(result_image_bytes)}
