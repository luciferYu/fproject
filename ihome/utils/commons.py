#!/usr/bin/python3
# -*- coding:utf-8 -*-
#auth:zhiyi
from werkzeug.routing import BaseConverter

class RegexConverter(BaseConverter):
    """在路由中使用正则表达式进行提取参数的转换工具"""
    def __init__(self,url_map,*args):
        super(RegexConverter,self).__init__(url_map)
        regex =args[0]








if __name__ == '__main__':
    pass