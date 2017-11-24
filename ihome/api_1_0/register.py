#!/usr/bin/python3
# -*- coding:utf-8 -*-
# auth:zhiyi

# 导入蓝图api
from . import api
# 导入captha扩展包，生成验证码图片
from ihome.utils.captcha.captcha import captcha
# 导入redis
from ihome import redis_store, constants, db
# 导入falsk 内置的上下文
from flask import current_app, jsonify, make_response, request, session
# 导入自定义的状态吗
from ihome.utils.response_code import RET

import re, random

# 导入云通讯接口，实现发送短信
from ihome.utils import sms
from ihome.models import User


@api.route('imagecode/<image_code_id>', methods=['GET'])
def generate_image_code(image_code_id):
    '''
    生成图片验证码：
    1、调用captcha扩展包生成图片验证码，name,text,image
    2、在服务器本地保存图片验证码的内容，在缓存redis里存
    3、使用响应对象返回前端图片验证码
    :param image_code_id:
    :return:
    '''
    name, text, image = captcha.generate_captcha()
    # 在服务器存储图片验证码的内容
    try:
        redis_store.setex('ImageCode_' + image_code_id, constants.IMAGE_CODE_REDIS_EXPIRES, text)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='保存图片验证码失败')
    # 返回前端图片验证码,需要使用响应对象
    else:
        response = make_response(image)
        # 设置响应对象的类型
        response.headers['Content-Type'] = 'image/jpg'
        # 返回前端图片验证码
        return response


@api.route('smscode/<mobile>', methods=['GET'])
def send_sms_code(mobile):
    '''
    发送短信 获取参数/校验参数\查询数据\返回结果
    1/获取参数，查询字符串的参数获取 ，text，id,request.args.get('text')
    2/校验参数，首先校验参数是否存在
    3/进一步校验手机号，正则表达式，re.match(r'^1[]$',mobile)
    4/校验图片验证码：获取本地存储的真是图片验证码
    5/判断获取结果，如果图片验证码过期结束程序
    6/删除图片验证码
    7/比较图片验证码：统一转成小谢比较图片验证码内容是否一致
    8/生成短信吗：使用random模块 随机数
    9/在本地保存短信验证码的内容
    10/调用云通讯发送短信：try except 中 使用异常进行处理
    11/保存云通讯的发送结果，判断是否发送成功
    12/返回前端结果
    :param mobile:
    :return:
    '''

    # 获取参数，mobile，text，id
    image_code = request.args.get('text')
    image_code_id = request.args.get('id')
    # 校验参数是否存在
    # all判断所有参数必须存在 any 判断只需要一个
    if not all([mobile, image_code, image_code_id]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数确实')
    # 校验手机号
    if not re.match(r'1[345789]\d{9}$', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg='手机号格式错误')
    # 校验图片验证码，获取本地存储的真是图片验证码
    try:
        real_image_code = redis_store.get('ImageCode_' + image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='获取图片验证码异常')
    # 判断获取结果
    if not real_image_code:
        return jsonify(errno=RET.DATAEXIST, errmsg='获取图片验证码过期')
    # 图片验证码只能获取一次，无论是否获取到，都必须删除图片验证码
    try:
        redis_store.delete('ImageCode_' + image_code_id)
    except Exception as e:
        current_app.logger.error(e)
    # 比较图片验证码的内容是否一致
    if real_image_code.lower() != image_code.lower():
        return jsonify(errno=RET.DATAERR, errmsg='图片验证码错误')
    # 生成短信随机码使用随机数 生成6位数
    sms_code = '%06d' % random.randint(1, 999999)
    # 保存短信验证码
    try:
        redis_store.setex('SMSCode_' + mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='保存短信验证码失败')

    # 判断用户是否已存在
    # 导入数据库实例
    from ihome.models import User
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询用户信息异常')
    else:
        if user is not None:
            return jsonify(errno=RET.DATAEXIST, errmsg='用户已经注册')

    # 发送短信，调用云通讯接口
    try:
        # 实例化对象
        ccp = sms.CCP()
        # 调用云通讯发送短信方法
        result = ccp.send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES], 1)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg='发送短信异常')
    # 判断发送结果
    if 0 == result:
        return jsonify(errno=RET.OK, errms='发送成功')
    else:
        return jsonify(errno=RET.THIRDERR, errms='发送失败')


@api.route('/users', methods=['POST'])
def register():
    '''
    注册
    :return:
    '''
    # 1/获取参数，获取post请求的参数，get_json()
    user_data = request.get_json()

    # 2/校验参数,参数存在
    if not user_data:
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')
    # 3/进一步解析详细的参数信息
    mobile = user_data.get('mobile')
    sms_code = user_data.get('sms_code')
    password = user_data.get('password')
    # 4/校验参数的完整性
    if not all([mobile, sms_code, password]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数缺失')
    # 5/校验手机号格式
    if not re.match(r'1[345789]\d{9}$', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg='手机号错误')

        # 10/判断用户是否已注册
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询用户信息异常')
    else:
        if user:
            return jsonify(errno=RET.DATAERR, errmsg='手机号已注册')

    # 6/校验短信验证码，获取本地存储的短信验证码
    try:
        real_sms_code = redis_store.get('SMSCode_' + mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='获取短信验证码异常')
    # 7/判断查询结果
    if not real_sms_code:
        return jsonify(errno=RET.DATAERR, errmsg='短信验证码过期')

    # 8/如果有数据，比较短信验证码
    if real_sms_code != str(sms_code):
        return jsonify(errno=RET.DATAERR, errmsg='短信验证码错误')
    # 9/删除已经验证过的短信验证码
    try:
        redis_store.delete('SMSCode_' + mobile)
    except Exception as e:
        current_app.logger.error(e)

    # 11/保存用户信息，User(name=mobile,mobile=mobile),user.password = password
    user = User()
    user.mobile = mobile
    user.name = mobile
    user.password = password
    # 12/提交数据到数据库中，事务操作，如果失败进行回滚
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg='保存用户信息')
    # 13/缓存用户信息 user_id,name,mobile
    session['user_id'] = user.id
    session['name'] = mobile
    session['mobile'] = mobile

    # 14/返回结果，user.to_dict()
    return jsonify(errno=RET.OK, errmsg='注册成功', data=user.to_dict())


if __name__ == '__main__':
    pass
