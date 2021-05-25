from urllib.parse import urlencode, parse_qs
from django.conf import settings
from urllib.request import urlopen
import json
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadData

from .exceptions import QQAPIException
from . import constants


import logging
# 日志记录器
logger = logging.getLogger('django')


class QQOauth(object):
    """QQ登录的工具类，内部封装业务逻辑的过程"""

    def __init__(self, client_id=None, client_secret=None, redirect_uri=None, state=None):
        """构造方法：接受在够到对象时初次传入的参数"""
        self.client_id = client_id or settings.QQ_CLIENT_ID
        self.client_secret = client_secret or settings.QQ_CLIENT_SECRET
        self.redirect_uri = redirect_uri or settings.QQ_REDIRECT_URI
        self.state = state or settings.QQ_STATE


    def get_login_url(self):
        """获取login_url
        # login_url = https://graph.qq.com/oauth2.0/authorize?response_type=code&client_id=101474184
        &redirect_uri=xx&state=next参数&scope=get_user_info
        """

        # 准备url
        url = 'https://graph.qq.com/oauth2.0/authorize?'

        # 准备请求参数
        params = {
            'response_type':'code',
            'client_id':self.client_id,
            'redirect_uri':self.redirect_uri,
            'state':self.state,
            'scope':'get_user_info'
        }

        # 将params字典转成查询字符串
        query_params = urlencode(params)

        # 使用url拼接请求参数
        login_url = url + query_params

        return login_url

    def get_access_token(self, code):
        """
        使用code获取access_token
        :param code: authorization code
        :return: access_toekn
        """
        # 准备url
        url = 'https://graph.qq.com/oauth2.0/token?'

        # 准备参数
        params = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.redirect_uri
        }

        # 拼接请求地址
        # url = url + urlencode(params)
        url += urlencode(params)

        # 美多商城给QQ服务器发送GET请求，获取access_token
        try:
            # response_data = (bytes)'access_token=FE04************************CCE2&expires_in=7776000&refresh_token=88E4************************BE14'
            response_data = urlopen(url).read()
            # (str)'access_token=FE04************************CCE2&expires_in=7776000&refresh_token=88E4************************BE14'
            response_str = response_data.decode()
            # 尽量的将response_str，转成字典，方便读取access_token
            response_dict = parse_qs(response_str)
            # 读取access_token
            access_token = response_dict.get('access_token')[0]
        except Exception as e:
            logger.error(e)
            # 在我们定义工具类中的工具方法的时候，如果出现了异常，直接抛出异常,谁使用我的工具谁捕获异常并解决
            # 类比 BookInfo.objects.get(id=13468954890965468909765) ==> DoesNotExist
            raise QQAPIException('获取access_token失败')

        # 返回access_token
        return access_token

    def get_openid(self, access_token):
        """
        使用access_token获取openid
        :param access_token: 获取openid的凭据
        :return: openid
        """
        # 准备url
        url = 'https://graph.qq.com/oauth2.0/me?access_token=%s' % access_token

        response_str = ''
        try:
            # 发送GET请求，获取openid
            # (bytes)'callback( {"client_id":"YOUR_APPID","openid":"YOUR_OPENID"} );'
            response_data = urlopen(url).read()
            # (str)'callback( {"client_id":"YOUR_APPID","openid":"YOUR_OPENID"} );'
            response_str = response_data.decode()
            # 使用字符串的切片，将response_str中的json字符串切出来
            # 返回的数据 callback( {"client_id":"YOUR_APPID","openid":"YOUR_OPENID"} )\n;
            response_dict = json.loads(response_str[10:-4])
            # 获取openid
            openid = response_dict.get('openid')
        except Exception as e:
            # 如果有异常，QQ服务器返回 "code=xxx&msg=xxx"
            err_data = parse_qs(response_str)
            logger.error(e)
            raise QQAPIException('code=%s msg=%s' % (err_data.get('code'), err_data.get('msg')))

        return openid

    @staticmethod
    def generate_save_user_token(openid):
        """
        生成保存用户数据的token
        :param openid: 用户的openid
        :return: token
        """
        serializer = Serializer(settings.SECRET_KEY, expires_in=constants.SAVE_QQ_USER_TOKEN_EXPIRES)
        data = {'openid': openid}
        token = serializer.dumps(data)
        return token.decode()

    @staticmethod
    def check_save_user_token(token):
        """
        检验保存用户数据的token
        :param token: token
        :return: openid or None
        """
        serializer = Serializer(settings.SECRET_KEY, expires_in=constants.SAVE_QQ_USER_TOKEN_EXPIRES)
        try:
            data = serializer.loads(token)
        except BadData:
            return None
        else:
            return data.get('openid')
























