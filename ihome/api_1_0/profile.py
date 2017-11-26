#!/usr/bin/python3
# -*- coding:utf-8 -*-
# auth:zhiyi
# 导入flask内置模块化方法
from flask import request, jsonify, current_app, session, g
from ihome.utils.response_code import RET

# 导入蓝图对象api
from . import api
# 导入正则
import re

# 导入模型类
from ihome.models import User
# 导入登录验证装饰器
from ihome.utils.commons import login_required

# 导入七牛云接口
from ihome.utils.image_storage import storage

# 导入数据库实例
from ihome import db, constants


# 登录
@api.route('/sessions', methods=['POST'])
def login():
    '''
    登录：获取参数/校验参数/查询数据/返回结果
    1/获取post请求的参数，get_json()'''
    print('登录函数')
    user_data = request.get_json()

    # 2/校验参数存在
    if not user_data:
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')

    # 3/进一步获取详细的参数信息，mobile,password
    mobile = user_data.get('mobile')
    password = user_data.get('password')
    if not all([mobile, password]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数缺失')
    # 4/对手机号格式进行校验
    if not re.match(r'1[3456789]\d{9}$', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg='手机号格式错误')

    # 5/查询数据库，确认用户存在
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询用户信息异常')

    # 6/检查查询结果，对密码正确性进行校验user.check_password_hash(password)
    if user is None or not user.check_password(password):  # 如果用户不存在 或密码错误
        return jsonify(errno=RET.DATAERR, errmsg='用户名或密码错误')
    # 7/缓存用户信息，session['user_id']=user.id
    session['user_id'] = user.id
    session['name'] = mobile
    session['mobile'] = mobile
    # 8/返回结果
    print('登录成功逻辑')
    return jsonify(errno=RET.OK, errmsg='登录成功')


# 获取用户信息
@api.route('/user', methods=['GET'])
@login_required
def get_user_profile():
    '''
    获取用户信息
    :return:
    '''
    # 1/获取用户id
    # 通过g变量
    user_id = g.user_id
    # 2/根据用户id查询数据库
    try:
        # 3/根据用户id查询数据库，get(),filter_by()
        # User.query.filter_by(id=user_id).first()
        user = User.query.get(user_id)
    except Exception as e:
        return jsonify(errno=RET.DBERR, errmsg='获取用户信息异常')
    # 4/校验查询结果，判断是否有数据
    if user is None:
        return jsonify(errno=RET.NODATA, errmsg='无效操作')
    # 5/返回用户信息
    return jsonify(errno=RET.OK, errmsg='OK', data=user.to_dict())


# 上传用户头像
@api.route('/user/avatar', methods=['POST'])
@login_required
def set_avatar_url():
    '''
    设置用户头像信息
    :return:
    '''
    # 1/获取参数，avatar,userid,requsest.files.get('avatar') avatar是前端name=指定 {#ajaxform#}  $(this).ajaxsubmit()插件
    user_id = g.user_id
    avatar = request.files.get('avatar')
    # 2/校验参数不存在，返回错误
    if not avatar:
        return jsonify(errno=RET.PARAMERR, errmsg='图片未上传')
    # 3/读取图片数据 data = avatar.read()
    avatar_data = avatar.read()
    # 4/调用七牛云接口，上传用户头像
    try:
        image_name = storage(avatar_data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg='上传头像失败')
    else:
        # 5/保存用户头像信息到数据库
        try:
            # 使用update更新用户头像信息
            User.query.filter_by(id=user_id).update({'avatar_url': image_name})
            db.session.commit()
        except Exception as e:
            current_app.logger.error(e)
            db.session.rollback()
            return jsonify(errno=RET.DBERR, errmsg='保存用户头像数据异常')
        # 6/拼接用户头像图片的完整路径，七牛云外链域名+图片文件名
        image_url = constants.QINIU_DOMIN_PREFIX + image_name
        # 7/返回结果
        return jsonify(errno=RET.OK, errmsg='OK', data={'avatar_url': image_url})


# 修改用户名信息
@api.route('/user/name', methods=['PUT'])
@login_required
def change_user_profile():
    '''
    修改用户名信息
    :return:
    '''
    # 1/获取有参数，user_id,put请求的参数，request.get_json()
    user_id = g.user_id
    user_data = request.get_json()
    # 2/校验参数
    if not user_data:
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')

    name = user_data.get('name')
    if not name:
        return jsonify(errno=RET.PARAMERR, errmsg='参数缺失')

    # 3/查询数据库，update更新用户信息
    try:
        # 4/提交数据，
        db.query.filter_by(id=user_id).update({'name': name})
        db.session.commit()
    except Exception as e:
        # 如发生异常需要进行回滚操作
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg='更新用户信息失败')

    # 5/修改缓存中的用户信息 session['name']=name
    session['name'] = name
    # 6/返回结果
    return jsonify(errno=RET.OK, errmsg='OK', data={'name': name})


@api.route('/user/auth', methods=['POST'])
@login_required
def set_user_auth():
    '''
    设置用户实名信息
    :return:
    '''
    # 1/ 获取参数 user_id,post请求的用户真是姓名 real_name 和 身份信息 id_card
    user_id = g.user_id
    user_data = request.get_json()
    # 2/校验参数的存在
    if not user_data:
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')
    # 3/进一步获取详细的参数信息
    real_name = user_data.get('real_name')
    id_card = user_data.get('id_card')
    # 4/校验参数的完成性
    if not all([real_name, id_card]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数缺失')
    # TODO 验证身份证18位
    # 5/保存用户的实名信息 update更新
    try:
        # User.query.filter_by(id=user_id,real_name=None,id_card=None).update({'real_name':real_name,'id_card':id_card})
        User.query.filter_by(id=user_id, real_name=None, id_card=None).update(
            {'real_name': real_name, 'id_card': id_card})
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg='数据保存异常')
    # 6/返回结果
    return jsonify(errno=RET.OK, errmsg='OK')

#获取实名信息
@api.route('/user/auth', methods=['GET'])
@login_required
def get_user_auth():
    '''
    获取用户实名信息
    :return:
    '''
    # 1/ 获取参数 user_id = g.user_id
    user_id = g.user_id
    # 2/查询数据库，获取用户信息
    try:
        # User.query.get(user_id)
        user = User.query.filter_by(id=user_id).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询用户实名信息异常')
    # 3/校验查询结果完整性
    if user is None:
        return jsonify(errno=RET.NODATA, errmsg='无效操作')
    # 4/返回前端结果 user.auth_to_dict()
    return jsonify(errno=RET.OK, errmsg='OK', data=user.auth_to_dict())

#退出登录
@api.route('/session', methods=['DELETE'])
@login_required
def logout():
    '''
    退出登录
    清空登录用户的缓存信息
    :return:
    '''
    session.clear()
    return jsonify(errno=RET.OK, errmsg='OK')


if __name__ == '__main__':
    # current_app.logger.error(e)
    # return jsonify(errno=RET.,errmsg='')
    pass
