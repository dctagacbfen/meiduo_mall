from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_jwt.settings import api_settings
from rest_framework.generics import GenericAPIView

from .utils import QQOauth
from .models import OAuthQQUser
from .exceptions import QQAPIException
from . import serializers
# Create your views here.


import logging
# 日志记录器
logger = logging.getLogger('django')


# url(r'^qq/user/$', views.QQAuthUserView.as_view()), 
class QQAuthUserView(GenericAPIView):
    """用户扫码登录的回调处理"""

    # 指定序列化器
    serializer_class = serializers.QQAuthUserSerializer


    def get(self, request):
        # 提取code请求参数
        code = request.query_params.get('code')
        if code is None:
            return Response({'message':'缺少code'}, status=status.HTTP_400_BAD_REQUEST)

        # 创建QQOauth对象
        oauth = QQOauth()

        try:
            # 使用code向QQ服务器请求access_token
            access_token = oauth.get_access_token(code)

            # 使用access_token向QQ服务器请求openid
            open_id = oauth.get_openid(access_token)
        except QQAPIException as e:
            logger.error(e)
            return Response({'message': 'QQ服务异常'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # 使用openid查询该QQ用户是否在美多商城中绑定过用户
        try:
            # oauth_user : 是查询出来的一条记录，就是OAuthQQUser模型对象而已
            oauth_user = OAuthQQUser.objects.get(openid=open_id)
        except OAuthQQUser.DoesNotExist:
            # 如果openid没绑定美多商城用户，创建用户并绑定到openid
            # 需要对open_id进行签名计算，不让外界捕获到真实的open_id
            token = oauth.generate_save_user_token(open_id)

            # 将token响应给前端:access_token是自己将openid签名之后的key
            return Response({'access_token':token})
            # return Response({'open_id':open_id})
        else:
            # 如果openid已绑定美多商城用户，直接生成JWT token，并返回
            jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
            jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

            # 使用当前的注册用户user生成载荷，该载荷内部会有{"username":"", "user_id":"", "email":""}
            user = oauth_user.user # OAuthQQUser模型对象取出user
            payload = jwt_payload_handler(user)
            # JWT  token
            token = jwt_encode_handler(payload)

            return Response({
                'token':token,
                'user_id':user.id,
                'username':user.username
            })


    def post(self, request):
        """绑定用户到openid
        GenericAPIView
        """
        # 获取序列化器对象
        serializer = self.get_serializer(data=request.data)
        # 开启校验
        serializer.is_valid(raise_exception=True)
        # 保存校验结果，并接收
        user = serializer.save()

        # 生成JWT token，并响应
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER
        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)

        return Response({
            'token': token,
            'username': user.username,
            'user_id': user.id
        })


# url(r'^qq/authorization/$', views.QQAuthURLView.as_view()),
class QQAuthURLView(APIView):
    """提供用户用于登录到QQ服务器的二维码扫描界面网址"""

    def get(self, request):
        # login_url = https://graph.qq.com/oauth2.0/authorize?response_type=code&client_id=101474184
        # &redirect_uri=xx&state=next参数&scope=get_user_info

        # 获取用户的next参数
        next = request.query_params.get('next')

        # 创建QQOauth对象
        oauth = QQOauth(state=next)

        # 获取login_url
        login_url = oauth.get_login_url()

        # 响应login_url
        return Response({'login_url':login_url})
