import os

appname = 'codeflares'
basedir = os.path.abspath(os.path.dirname(__file__))
version = '0.0.1'


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', '79a9ba1db3988b1703b05fd4d2873516')
    BASEDIR = basedir
    APPNAME = appname
    DEBUG = False
    TESTING = False
    VERSION = version


class DevelopmentConfig(Config):
    ENV = 'development'
    DEBUG = True


class TestingConfig(Config):
    ENV = 'testing'
    DEBUG = True
    TESTING = True


class ProductionConfig(Config):
    ENV = 'production'
    DEBUG = True


instances = dict(
    production=ProductionConfig,
    testing=TestingConfig,
    development=DevelopmentConfig,
)
