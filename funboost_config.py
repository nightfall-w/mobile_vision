# -*- coding: utf-8 -*-
import logging
from urllib.parse import quote_plus

from funboost.utils.simple_data_class import DataClassBase
from nb_log import nb_log_config_default

from core.redis import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD

'''
funboost_config.py 文件是第一次运行框架自动生成到你的项目根目录的，不需要用由户手动创建。
此文件里面可以写任意python代码。例如 中间件 帐号 密码自己完全可以从apola配置中心获取或者从环境变量获取。
'''

'''
你项目根目录下自动生成的 funboost_config.py 文件中修改配置，会被自动读取到。
用户不要动修改框架的源码 funboost/funboost_config_deafult.py 中的代码，此模块的变量会自动被 funboost_config.py 覆盖。
funboost/funboost_config_deafult.py配置覆盖逻辑可看funboost/set_frame_config.py中的代码.

框架使用文档是 https://funboost.readthedocs.io/zh_CN/latest/
'''


class BrokerConnConfig(DataClassBase):
    """
    中间件连接配置
    """
    REDIS_HOST = REDIS_HOST
    REDIS_USERNAME = ''
    REDIS_PASSWORD = REDIS_PASSWORD
    REDIS_PORT = int(REDIS_PORT)
    REDIS_DB = 7
    REDIS_DB_FILTER_AND_RPC_RESULT = 8
    REDIS_SSL = False
    # 加上 socket_keepalive 参数防止 macOS/网络层断开空闲连接
    # health_check_interval 启动后台健康检查，socket_timeout 缩短读写超时
    REDIS_URL = (
        f'{"rediss" if REDIS_SSL else "redis"}://{REDIS_USERNAME}:{quote_plus(REDIS_PASSWORD)}'
        f'@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
        f'?socket_keepalive=true&socket_connect_timeout=10&socket_timeout=30'
        f'&health_check_interval=15&retry_on_timeout=true'
    )
    REDIS_SOCKET_TIMEOUT = 30
    REDIS_HEALTH_CHECK_INTERVAL = 15


class FunboostCommonConfig(DataClassBase):
    NB_LOG_FORMATER_INDEX_FOR_CONSUMER_AND_PUBLISHER = logging.Formatter(
        f'%(asctime)s-({nb_log_config_default.computer_ip},{nb_log_config_default.computer_name})-[p%(process)d_t%(thread)d] - %(name)s - "%(filename)s:%(lineno)d" - %(funcName)s - %(levelname)s - %(task_id)s - %(message)s',
        "%Y-%m-%d %H:%M:%S", )

    TIMEZONE = 'Asia/Shanghai'

    SHOW_HOW_FUNBOOST_CONFIG_SETTINGS = False
    FUNBOOST_PROMPT_LOG_LEVEL = logging.DEBUG
    KEEPALIVETIMETHREAD_LOG_LEVEL = logging.DEBUG
