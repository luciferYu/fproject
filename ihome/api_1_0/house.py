#!/usr/bin/python3
# -*- coding:utf-8 -*-
#auth:zhiyi
from . import api
#导入redis数据库实例
from ihome import  redis_store,constants,db
#导入flask内置的对象
from flask import current_app,jsonify,request,g
#导入模型类
from ihome.models import Area,House,Facility,HouseImage
#导入自定义状态吗
from ihome.utils.response_code import RET
import json
#导入登录验证装饰器
from ihome.utils.commons import login_required
#导入七牛云
from ihome.utils.image_storage import storage


@api.route('/areas',methods=['GET'])
def get_area_info():
    '''
    获取区域信息：首页区域信息加载 ---- 缓存数据库----磁盘数据库----缓存数据库
    :return:
    '''
    #1/尝试从redis中获取redis数据库的数据
    try:
        ret = redis_store.get('area_info')
    except Exception as e:
        current_app.logger.error(e)
        #把ret重设置为None
        ret = None

    #2/如果获取过程发生异常，要把获取结果重新设置为None值
    #3/判断获取结果，如果有数据直接返回，留下日志
    if ret:
        #记录访问redis数据库房屋区域信息的时间
        current_app.logger.info('hit area info redis')
        # 直接返回区域信息数据
        return '{"errno":0,"errmsg":"OK","data":%s}' % ret
    #4/查询mysql数据库，获取区域信息
    try:
        areas = Area.query.all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='获取区域信息失败')
    #5/校验查询结果
    if not areas:
        return jsonify(errno=RET.NODATA,errmsg='无区域信息')
    #定义列表存储查询结果
    areas_list =[]
    #遍历查询结果，调用模型类的实例方法，添加区域信息数据
    for area in areas:
        areas_list.append(area.to_dict())
    #6/对查询结果进行保存，遍历查询结果，调用模型类实例方法，添加区域信息，

    #7/序列化数据转成json，存入缓存中
    areas_json = json.dumps(areas_list)
    try:
        redis_store.setex('area_info',constants.AREA_INFO_REDIS_EXPIRES,areas_json)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='缓存区域信息异常')
    #8/拼接字符串，直接返回区域信息的json数据
    resp = '{"errno":0,"errmsg":"OK","data":%s}' % areas_json
    return resp

@api.route('/houses',methods=['POST'])
@login_required
def save_house_info():
    '''
    发布新房源  获取参数/校验参数/查询数据/返回结果
    :return:
    '''
    #1/获取参数，user_id = g.user_id，获取post请求参数
    user_id = g.user_id
    #存储房屋数据
    house_data = request.get_json()
    #2/校验参数的存在
    if not house_data:
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')
    #3/获取详细参数信息，主要包括房屋的基本字段
    title = house_data.get('title') #房屋标题
    price = house_data.get('price') #房屋价格
    area_id = house_data.get('area_id') #房屋区域
    address = house_data.get('address')  #房屋地址
    room_count = house_data.get('room_count') #房间数目
    acreage = house_data.get('acreage')  #房屋面积
    unit = house_data.get('unit') #房屋户型
    capacity = house_data.get('capacity') #房屋适住人数
    beds = house_data.get('beds')  #房屋卧床配置
    deposit = house_data.get('deposit')  #房屋押金
    min_days = house_data.get('min_days') #房屋最小入住天数
    max_days= house_data.get('max_days')  #房屋最大入住天数

    if not all([title,price,area_id,address,room_count,acreage,unit,capacity,beds,deposit,min_days,max_days]):
        return jsonify(errno=RET.PARAMERR, errmsg='房屋参数缺失')


    #4/对参数的校验，对价格进行单位转换，由元转成分
    try:
        price = int(float(price)*100)
        deposit = int(float(deposit)*100)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg='价格参数异常')

    #5/临时保存房屋数据，构造模型类对象，存储房屋的基本信息，db.session.add(house)
    house = House()
    house.title = title
    house.user_id = user_id
    house.area_id = area_id
    house.price = price
    house.address = address
    house.room_count = room_count
    house.acreage = acreage
    house.unit = unit
    house.capacity = capacity
    house.beds = beds
    house.deposit = deposit
    house.min_days = min_days
    house.max_days = max_days

    #6/尝试获取配套设施信息，如果有数据，对设施进行过滤操作
    facility = house_data.get('facility')
    if facility:
        # 过滤配套设施编号
        try:
            facilities = Facility.query.filter(Facility.id.in_(facility)).all()
            #保存房屋设施信息
            # 7/存储配套设施信息，house.facilities = facilites
            house.facilities = facilities
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR,errmsg='查询配套设施异常')


    #8/提交数据到数据库
    try:
        db.session.add(house)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg='保存房屋信息失败')
    #9/返回结果 需要返回房屋id
    return jsonify(errno=RET.OK,errmsg='OK',data={"house_id":house.id})

@api.route('/houses/<int:house_id>/images',methods=['POST'])
@login_required
def save_house_image(house_id):
    '''
    保存房屋图片
    :param house_id:
    :return:
    '''
    #1/获取参数，房屋id 获取用户上传的图片 request.files.get('house_image')
    image = request.files.get('house_image')
    if not image:
        return jsonify(errno=RET.PARAMERR, errmsg='图片未上传')
    #2/通过house_id，保存房屋图片，查询数据库确认房屋存在
    try:
        house = House.query.filter_by(id=house_id).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询房屋数据异常')
    #3/校验查询结果
    if not house:
        return jsonify(errno=RET.NODATA, errmsg='房屋数据不存在')
    #4/读取图片数据
    image_data = image.read()
    #5/调用七牛云接口，上传房屋图片
    try:
        image_name = storage(image_data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg='上传图片失败')
    #6/保存房屋图片，house_image = HouseImage()
    house_image = HouseImage()
    house_image.house_id = house_id
    house_image.url = image_name
    db.session.add(house_image)
    #7/保存房屋图片到房屋表，主图片设置判断 首页需要展示房屋幻灯片信息，添加猪图片设置
    if not house.index_image_url:
        house.index_image_url = image_name
        db.session.add(house)
    #8/提交数据到数据库，如果发生异常需要进行回滚
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback() # 回滚操作
        return jsonify(errno=RET.DBERR, errmsg='存入房屋图片数据异常')
    #9/拼接路径，返回前端图片url
    image_url = constants.QINIU_DOMIN_PREFIX + image_name
    return jsonify(errno=RET.OK, errmsg='OK',data={"url":image_url})





if __name__ == '__main__':
    #current_app.logger.error(e)
    # return jsonify(errno=RET.,errmsg='')
    pass