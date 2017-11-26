#!/usr/bin/python3
# -*- coding:utf-8 -*-
#auth:zhiyi
from flask import Blueprint,make_response,current_app
from flask_wtf import csrf

html = Blueprint('html',__name__)

@html.route("/<regex('.*'):file_name>")
def html_file(file_name):
    print('进入html_file函数')
    if not file_name:
        print('进入首页逻辑')
        file_name = '/index.html'

    if file_name != 'favicon.ico':
        file_name = 'html/' + file_name

    csrf_token = csrf.generate_csrf()
    response =  make_response(current_app.send_static_file(file_name))
    response.set_cookie('csrf_token',csrf_token)
    return response

if __name__ == '__main__':
    pass