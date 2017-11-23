#!/usr/bin/python3
# -*- coding:utf-8 -*-
#auth:zhiyi
from flask import Flask
from config import config,Config
from .utils.commons import RegexConverter
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_session import Session
#创建数据库对象
db = SQLAlchemy()
# 使用wtf提供的csrf保护机制
csrf = CSRFProtect()


def create_app(config_name):
    '''
    创建flask应用app对象
    :param config_name:传入运行的环境 例如：development 或者 production
    :return:
    '''
    app = Flask(__name__)
    # 从配置对象中为app设置配置信息
    app.config.from_object(config[config_name])

    # 为app中的url路由添加正则表达式匹配
    app.url_map.converters["regex"] = RegexConverter

    # 数据库处理
    db.init_app(app)

    # 为app添加CSRF保护
    csrf.init_app(app)

    # 使用flask-session扩展，用redis保存app的session数据
    Session(app)

    #为app添加api蓝图应用
    from .api_1_0 import api as api_1_0_blueprint
    app.register_blueprint(api_1_0_blueprint, url_prefix="/api/v1.0")

    # 为app添加返回静态html的蓝图应用
    from .web_page import html as html_blueprint
    app.register_blueprint(html_blueprint)

    return app



if __name__ == '__main__':
    pass