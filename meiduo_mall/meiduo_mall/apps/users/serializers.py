from rest_framework import serializers
import re
from django_redis import get_redis_connection
from rest_framework_jwt.settings import api_settings

from .models import User, Address
from celery_tasks.email.tasks import send_verify_email


class UserAddressSerializer(serializers.ModelSerializer):
    """
    用户地址序列化器
    """
    province = serializers.StringRelatedField(read_only=True)
    city = serializers.StringRelatedField(read_only=True)
    district = serializers.StringRelatedField(read_only=True)
    province_id = serializers.IntegerField(label='省ID', required=True)
    city_id = serializers.IntegerField(label='市ID', required=True)
    district_id = serializers.IntegerField(label='区ID', required=True)

    class Meta:
        model = Address
        exclude = ('user', 'is_deleted', 'create_time', 'update_time')

    def validate_mobile(self, value):
        """
        验证手机号
        """
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号格式错误')
        return value

    def create(self, validated_data):
        """
        保存
        """
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class AddressTitleSerializer(serializers.ModelSerializer):
    """
    地址标题
    """
    class Meta:
        model = Address
        fields = ('title',)


class EmailSerializer(serializers.ModelSerializer):
    """添加邮箱的序列化器和反序列化"""

    class Meta:
        model = User
        fields = ['id', 'email']

        extra_kwargs = {
            # 因为email字段可以在数据库中为空，所以ModelSerializer在映射User的email字段时，默认指定的在输入时可以不传
            # 但是，本次需要更新的就是email,所以要更新为必传字段
            'email': {
                'required': True
            }
        }

    def update(self, instance, validated_data):
        """
        更新数据时自动调用的
        :param instance: 是外界的序列化器初始化时传入的模型对象 ，这里指的是登录用户的user对象
                （serializer = self.get_serializer(instance, data=request.data, partial=partial)）
                (serializer.save())
        :param validated_data: 经过验证之后的数据，这里指的是email
        :return: 返回{"id":"", "email":""}
        """
        # instance == user对象

        instance.email = validated_data.get('email')
        instance.save()

        # 在保存邮件事件中，响应保存邮件结果之前，异步发送邮件

        # 生成用户用于点击的验证连接
        verify_url = instance.generate_verify_email_url()

        # 注意：一定要记得调用delay
        send_verify_email.delay(instance.email, verify_url)

        return instance


class UserDetailSerializer(serializers.ModelSerializer):
    """用户基本信息的序列化器：用于序列化的"""

    class Meta:
        model = User
        fields = ['id', 'username', 'mobile', 'email', 'email_active']


class CreateUserSerializer(serializers.ModelSerializer):
    """创建用户的序列化器"""

    # 指定模型类以外的字段
    password2 = serializers.CharField(label='确认密码', write_only=True)
    sms_code = serializers.CharField(label='短信验证码', write_only=True)
    allow = serializers.CharField(label='同意协议', write_only=True)
    # 增加token字段:只做输出
    token = serializers.CharField(label='登录状态token', read_only=True)

    class Meta:
        model = User
        # ['id', 'username', 'mobile'] : 输出 read_only
        # ['password', 'password2', 'sms_code', 'allow'] : 输入 write_only
        fields = ['id', 'username', 'mobile', 'password', 'password2', 'sms_code', 'allow', 'token']

        # 追加额外的校验
        extra_kwargs = {
            'username': {
                'min_length': 5,
                'max_length': 20,
                'error_messages': {
                    'min_length': '仅允许5-20个字符的用户名',
                    'max_length': '仅允许5-20个字符的用户名',
                }
            },
            'password': {
                'write_only': True,
                'min_length': 8,
                'max_length': 20,
                'error_messages': {
                    'min_length': '仅允许8-20个字符的密码',
                    'max_length': '仅允许8-20个字符的密码',
                }
            }
        }

    def validate_mobile(self, value):
        """验证手机号"""
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号格式错误')
        return value

    def validate_allow(self, value):
        """检验用户是否同意协议"""
        if value != 'true':
            raise serializers.ValidationError('请同意用户协议')
        return value

    def validate(self, data):
        # 判断两次密码
        if data['password'] != data['password2']:
            raise serializers.ValidationError('两次密码不一致')

        # 判断短信验证码
        redis_conn = get_redis_connection('verify_codes')
        mobile = data['mobile']
        real_sms_code = redis_conn.get('sms_%s' % mobile)
        if real_sms_code is None:
            raise serializers.ValidationError('无效的短信验证码')
        if data['sms_code'] != real_sms_code.decode():
            raise serializers.ValidationError('短信验证码错误')

        return data

    def create(self, validated_data):
        """
        创建用户
        重写create的目的是为了剔除掉，为只读的字段，但是不在数据库中的额字段
        """
        # 移除数据库模型类中不存在的属性
        del validated_data['password2']
        del validated_data['sms_code']
        del validated_data['allow']
        user = super().create(validated_data)

        # 调用django的认证系统加密密码
        user.set_password(validated_data['password'])
        user.save()

        # 在注册数据保存完成，响应注册数据之前，生成JWT token
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

        # 使用当前的注册用户user生成载荷，该载荷内部会有{"username":"", "user_id":"", "email":""}
        payload = jwt_payload_handler(user)
        # JWT  token
        token = jwt_encode_handler(payload)

        # 将token临时绑定到user模型对象，顺便响应给用户
        user.token = token

        return user