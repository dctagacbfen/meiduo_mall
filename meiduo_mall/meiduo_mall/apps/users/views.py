from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action

from .models import User
from . import serializers
from . import constants
# Create your views here.


class AddressViewSet(mixins.CreateModelMixin, mixins.UpdateModelMixin, GenericViewSet):
    """
    用户地址新增与修改
    """
    serializer_class = serializers.UserAddressSerializer
    permissions = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.addresses.filter(is_deleted=False)

    # GET /addresses/
    def list(self, request, *args, **kwargs):
        """
        用户地址列表数据
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        user = self.request.user
        return Response({
            'user_id': user.id,
            'default_address_id': user.default_address_id,
            'limit': constants.USER_ADDRESS_COUNTS_LIMIT,
            'addresses': serializer.data,
        })

    # POST /addresses/
    def create(self, request, *args, **kwargs):
        """
        保存用户地址数据
        """
        # 检查用户地址数据数目不能超过上限
        count = request.user.addresses.count()
        if count >= constants.USER_ADDRESS_COUNTS_LIMIT:
            return Response({'message': '保存地址数据已达到上限'}, status=status.HTTP_400_BAD_REQUEST)

        return super().create(request, *args, **kwargs)

    # delete /addresses/<pk>/
    def destroy(self, request, *args, **kwargs):
        """
        处理删除
        """
        address = self.get_object()

        # 进行逻辑删除
        address.is_deleted = True
        address.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

    # put /addresses/pk/status/
    @action(methods=['put'], detail=True)
    def status(self, request, pk=None):
        """
        设置默认地址
        """
        address = self.get_object()
        request.user.default_address = address
        request.user.save()
        return Response({'message': 'OK'}, status=status.HTTP_200_OK)

    # put /addresses/pk/title/
    # 需要请求体参数 title
    @action(methods=['put'], detail=True)
    def title(self, request, pk=None):
        """
        修改标题
        """
        address = self.get_object()
        serializer = serializers.AddressTitleSerializer(instance=address, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class VerifyEmailView(APIView):
    """验证邮箱
    目的：获取用户的token,读取出token中的user信息，将user查询出来修改email_active字段的值为True
    """
    def get(self, request):
        # 获取用户的token
        # token=eyJhbGciOiJIUzI1NiIsImlhdCI6MTUzMjMxNjk4MywiZXhwIjoxNTMyNDAzMzgzfQ.eyJ1c2VyX2lkIjoyLCJlbWFpbCI6InpoYW5namllc2hhcnBAMTYzLmNvbSJ9.IoeHdBuAo35ZbigZpVBvMSUh-Qp4TCNy0JXbg4TZmdY
        token = request.query_params.get('token')
        if token is None:
            return Response({'message':'缺少token'}, status=status.HTTP_400_BAD_REQUEST)

        # 读取出token中的user信息
        # {'user_id':1, 'email':'zhangjiesharp@163.com'}
        user = User.check_verify_email_token(token)
        if user is None:
            return Response({'message': '无效token'}, status=status.HTTP_400_BAD_REQUEST)

        # 将user查询出来修改email_active字段的值为True
        user.email_active = True
        user.save()

        # 响应修改结果：修改数据状态码成功是200
        return Response({'message':'OK'})


class EmailView(UpdateAPIView):
    """添加邮箱"""

    # 指定权限：只有登录用户才能访问该接口
    permission_classes = [IsAuthenticated]

    # 指定序列化器
    serializer_class = serializers.EmailSerializer

    def get_object(self):
        """
        因为目前没有定义put方法，没有传递pk给RetrieveAPIView
        但是，UpdateAPIView里面的get_object()方法需要得到当前的登录用户是谁
        所以重写这个方法，告诉UpdateAPIView里面的get_object()方法，当前的登录用户是谁
        """
        return self.request.user


class UserDetailView(RetrieveAPIView):
    """用户基本信息"""

    # 指定权限：只有登录用户才能访问该接口
    permission_classes = [IsAuthenticated]

    # 指定序列化器
    serializer_class = serializers.UserDetailSerializer

    def get_object(self):
        """
        因为目前没有定义get方法，没有传递pk给RetrieveAPIView
        但是，RetrieveAPIView里面的get_object()方法需要得到当前的登录用户是谁
        所以重写这个方法，告诉RetrieveAPIView里面的get_object()方法，当前的登录用户是谁
        :return: 
        """
        return self.request.user

    # def get(self, request):
    #     """提供用户基本信息
    #     查询出当前登录用户user数据
    #     使用序列化器序列化user数据
    #     响应数据
    #     """
    #     pass


class UserView(CreateAPIView):
    """注册"""

    # 指定序列化器
    serializer_class = serializers.CreateUserSerializer


# url(r'^mobiles/(?P<mobile>1[3-9]\d{9})/count/$', views.MobileCountView.as_view()),
class MobileCountView(APIView):
    """
    手机号数量
    """
    def get(self, request, mobile):
        """
        获取指定手机号数量
        """
        count = User.objects.filter(mobile=mobile).count()

        data = {
            'mobile': mobile,
            'count': count
        }

        return Response(data)


# url(r'^usernames/(?P<username>\w{5,20})/count/$', views.UsernameCountView.as_view()),
class UsernameCountView(APIView):
    """
    用户名数量
    """
    def get(self, request, username):
        """
        获取指定用户名数量
        """
        count = User.objects.filter(username=username).count()

        data = {
            'username': username,
            'count': count
        }

        return Response(data)
