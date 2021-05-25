# celery的启动文件
from celery import Celery


# 为celery使用django配置文件进行设置
import os
if not os.getenv('DJANGO_SETTINGS_MODULE'):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'meiduo_mall.settings.dev'

# 创建celery实例:参数是celery的别名，没有实际的意义
celery_app = Celery('meiduo_03')

# 加载配置
celery_app.config_from_object('celery_tasks.config')

# 指定异步任务
celery_app.autodiscover_tasks(['celery_tasks.sms', 'celery_tasks.email'])
