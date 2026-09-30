#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HivisionIDPhotos API 启动脚本（独立于 deploy_api.py，支持自定义端口）
用法: ./.venv/bin/python run_api_8081.py [port]
默认端口 8081（本机 8080 被糯米 llama-server 占用）
"""
import os
import sys
import uvicorn

from deploy_api import app
from cloud_api import router as cloud_router

# 挂载云托管 callContainer JSON 兼容端点（/api/idphoto、/api/add_background）
app.include_router(cloud_router)

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", "8081"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
