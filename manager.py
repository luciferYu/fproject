#!/usr/bin/python3
# -*- coding:utf-8 -*-
#auth:zhiyi
# 项目启动文件
from ihome import create_app,db
from flask_migrate import Migrate,MigrateCommand
from flask_script import Manager
from ihome import models
import pymysql
pymysql.install_as_MySQLdb() #引入mysql安装文件

app = create_app('development')

Migrate(app,db)
manager = Manager(app)
manager.add_command('db',MigrateCommand)



if __name__ == '__main__':
    print(app.url_map)
    manager.run()