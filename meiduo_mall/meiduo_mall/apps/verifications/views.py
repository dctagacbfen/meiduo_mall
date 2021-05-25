from django.shortcuts import render
from rest_framework.views import APIView
from django_redis import get_redis_connection
from django.http import HttpResponse
import random
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView


from meiduo_mall.libs.captcha.captcha import captcha
from . import constants
from meiduo_mall.libs.yuntongxun.sms import CCP
from . import serializers
from celery_tasks.sms.tasks import send_sms_code
# Create your views here.


import logging
# 日志记录器
logger = logging.getLogger('django')


# url('^sms_codes/(?P<mobile>1[3-9]\d{9})/$', views.SMSCodeView.as_view()),
class SMSCodeView(GenericAPIView):
    """短信验证码"""

    # 指定序列化器
    serializer_class = serializers.ImageCodeCheckSerializer

    def get(self, request, mobile):
        """发送短信验证码"""
        # 接受参数：mobile,image_code_id,text
        # 校验参数：比较用户传入的图片验证码和服务器存储的是否一致

        # 创建序列化器对象
        # request.query_params == ?image_code_id=xx&text=oo
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        # 生成随机的短信验证码:6位验证码，不够6位需要补0
        sms_code = '%06d' % random.randint(0, 999999)
        logger.info(sms_code)

        # 发送短信验证码:"您的验证码为sms_code，请constants.SMS_CODE_REDIS_EXPIRES分钟之内输入"
        # 对接第三方平台，是个延时的操作，不能让该延时的操作阻塞后续代码的执行
        # CCP().send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES // 60], 1)

        # celery异步发送短信
        # delay : 会将异步任务添加到redis,表示用户触发了异步任务，worker就知道此时需要去redis中读取任务
        # send_sms_code.delay(mobile, sms_code)

        # 存储短信验证码
        redis_conn = get_redis_connection('verify_codes')

        # redis_conn.setex('sms_%s' % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        #
        # # 给每个手机号码绑定一个数值，数值的生命周期是60s，用于标识用户是否使用同一个手机号码频繁发送短信
        # redis_conn.setex('send_flag_%s' % mobile, constants.SEND_SMS_CODE_INTERVAL, 1)

        # 使用redis管道的概念,将多个redis指令整合到一起执行,提升redis访问的效率,多个指令只需要访问一次redis
        pl = redis_conn.pipeline()

        # 存储短信验证码
        pl.setex('sms_%s' % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        # 给每个手机号码绑定一个数值，数值的生命周期是60s，用于标识用户是否使用同一个手机号码频繁发送短信
        pl.setex('send_flag_%s' % mobile, constants.SEND_SMS_CODE_INTERVAL, 1)

        # 注意：记得调用execute()
        pl.execute()

        # 响应发送短信验证码结果
        return Response({'message':'OK'})


# url(r'image_codes/(?P<image_code_id>[\w-]+)/', views.ImageCodeView.as_view()),
class ImageCodeView(APIView):
    """图片验证码"""

    def get(self, request, image_code_id):
        """提供图片验证码"""

        # 生成图片验证码内容和图片
        text, image = captcha.generate_captcha()
        logger.info(text)

        # 将图片验证码内容保存到redis
        redis_conn = get_redis_connection('verify_codes')
        redis_conn.set('img_%s' % image_code_id, text, constants.IMAGE_CODE_REDIS_EXPIRES)

        # 将图片验证码的图片响应给用户(image/jpg)
        return HttpResponse(image, content_type='image/jpg')
