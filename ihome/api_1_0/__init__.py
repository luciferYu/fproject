#!/usr/bin/python3
# -*- coding:utf-8 -*-
#auth:zhiyi

from flask import Blueprint
api = Blueprint('api',__name__)
#蓝图使用
#1创建蓝图对象
#2使用蓝图对象（如果再次拆分文件，需要把拆分出去的文件，再导入创建蓝图对象文件中）
#3注册蓝图对象
from . import register,profile,house

@api.after_request
def after_request(response):
    """设置默认的响应报文格式为application/json"""
    # 如果响应报文response的Content-Type是以text开头，则将其改为默认的json类型
    if response.headers.get("Content-Type").startswith("text"):
        response.headers["Content-Type"] = "application/json"
    return response



if __name__ == '__main__':
    pass