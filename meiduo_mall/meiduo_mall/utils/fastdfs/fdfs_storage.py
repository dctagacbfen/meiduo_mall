from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client
from django.conf import settings


class FastDFSStorage(Storage):
    """自定义文件存储系统"""

    def __init__(self, client_conf=None, base_url=None):
        self.client_conf = client_conf or settings.FDFS_CLIENT_CONF
        self.base_url = base_url or settings.FDFS_BASE_URL

    def _open(self, name, mode='rb'):
        """打开文件时会自动调用的方法
        因为这个类是实现存储，不涉及到文件的打开，所以这个方法用不到，但是，必须文档告诉我必须实现，所以pass
        """
        pass

    def _save(self, name, content):
        """
        文件要存储时会自动的调用的方法：借此机会将要存储的文件上传到fastdfs
        :param name: 要存储的文件的名字
        :param content: 要存储的文件对象，是File类型的对象，需要调用read()读取出里面的文件内容二进制
        :return: file_id
        """
        # 创建fdfs客户端
        # client = Fdfs_client('meiduo_mall/utils/fastdfs/client.conf')
        client = Fdfs_client(self.client_conf)

        # 调用上传的方法:upload_by_buffer()是使用文件的二进制上传的
        ret = client.upload_by_buffer(content.read())

        # 判断文件上传是否成功
        if ret.get('Status') != 'Upload successed.':
            raise Exception('fastfds upload error')

        # 如果上传成功就将file_id返回出去
        file_id = ret.get('Remote file_id')

        # 本次return会将file_id自动的存储到ImageField字段对应的模型属性中，并自动的同步到数据库
        return file_id

    def exists(self, name):
        """告诉Django文件是否存在
        本次的文件的存储需要转存到fastdfs,不需要在本地存储，所以每次要存储某个文件时，都需要返回False
        返回False,是告诉Django本地没有的，那么Django才会去存储，才会去调用save()方法
        """
        return False

    def url(self, name):
        """
        需要在这个方法中，拼接文件的全路径，用于将来做文件的下载的
        <img src="{{ content.image.url }}">
        :param name: 文件的名字：group1/M00/00/00/wKhnhFtWKcOAcNjGAAC4j90Tziw97.jpeg
        :return: 文件的全路径：http://192.168.103.132:8888/group1/M00/00/00/wKhnhFtWKcOAcNjGAAC4j90Tziw97.jpeg
        """
        # return 'http://192.168.103.132:8888/' + name
        return self.base_url + name