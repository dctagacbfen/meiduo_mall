from django.conf.urls import url

from . import views



urlpatterns = [
    # 提供用户用于登录到QQ服务器的二维码扫描界面的网址
    url(r'^qq/authorization/$', views.QQAuthURLView.as_view()),
    # 处理回调
    url(r'^qq/user/$', views.QQAuthUserView.as_view()),
]