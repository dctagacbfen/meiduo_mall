# 定义具体的异步任务的文件
# 定义异步任务的文件必须叫tasks.py
from . import constants
from celery_tasks.sms.yuntongxun.sms import CCP
from celery_tasks.main import celery_app

# 使用装饰器将该方法注册为celery_app可识别的任务,并起别名，没有实际的意义
@celery_app.task(name='send_sms_code')
def send_sms_code(mobile, sms_code):
    # 异步的发送短信
    CCP().send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES // 60], 1)

