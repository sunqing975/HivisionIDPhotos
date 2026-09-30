#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HivisionIDPhotos API 验证脚本（最终版）
用法: HIVISION_API=http://127.0.0.1:8082 ./.venv/bin/python test/verify_api.py
流程: 上传测试图 → /idphoto 抠图 → /add_background 换底色 → 校验返回并落盘
注意:
- /idphoto 用 multipart 传 input_image 文件
- /add_background 的 input_image_base64/color 是 Form 字段，可用 urlencoded 或 multipart
- 返回的 base64 带 "data:image/png;base64," 前缀，需剥离后再解码
"""
import base64
import os
import sys

import requests

BASE = os.environ.get("HIVISION_API", "http://127.0.0.1:8082")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_IMG = os.path.join(ROOT, "assets", "portrait_test.jpg")
OUT_DIR = os.path.join(ROOT, "test", "temp")


def clean_b64(s):
    """剥离 data URI 前缀并补齐 padding"""
    if not s:
        return ""
    if s.startswith("data:"):
        s = s.split(",", 1)[1]
    return s + "=" * (-len(s) % 4)


def main():
    if not os.path.exists(TEST_IMG):
        sys.exit(f"测试图不存在: {TEST_IMG}")
    os.makedirs(OUT_DIR, exist_ok=True)

    # 1. 生成透明底证件照（一寸 295x413）
    print("[1/3] POST /idphoto ...")
    with open(TEST_IMG, "rb") as f:
        resp = requests.post(
            BASE + "/idphoto",
            files={"input_image": ("portrait.jpg", f, "image/jpeg")},
            data={"height": "413", "width": "295", "hd": "true"},
            timeout=120,
        )
    if resp.status_code != 200:
        sys.exit(f"  ✗ HTTP {resp.status_code}: {resp.text[:300]}")
    body = resp.json()
    if not body.get("status"):
        sys.exit(f"  ✗ status=false: {body}")
    std = clean_b64(body.get("image_base64_standard", ""))
    with open(os.path.join(OUT_DIR, "idphoto_standard.png"), "wb") as f:
        f.write(base64.b64decode(std))
    print("  ✓ 透明底证件照已保存 idphoto_standard.png")

    # 2/3. 换红/白/蓝底色（urlencoded 模拟小程序调用）
    for color, name in [("FF0000", "red"), ("FFFFFF", "white"), ("438EDB", "blue")]:
        print(f"[{name}] POST /add_background color={color} ...")
        r2 = requests.post(
            BASE + "/add_background",
            data={"input_image_base64": std, "color": color},
            headers={"content-type": "application/x-www-form-urlencoded"},
            timeout=120,
        )
        b2 = r2.json()
        if not b2.get("status"):
            sys.exit(f"  ✗ status=false: {b2}")
        with open(os.path.join(OUT_DIR, f"add_background_{name}.jpg"), "wb") as f:
            f.write(base64.b64decode(clean_b64(b2["image_base64"])))
        print(f"  ✓ 已保存 add_background_{name}.jpg")

    print("\n全部接口验证通过 ✓ 输出目录:", OUT_DIR)


if __name__ == "__main__":
    main()
