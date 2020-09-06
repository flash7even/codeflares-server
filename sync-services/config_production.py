class ConfigProduction:
    SERVER_HOST = 'http://localhost:5056/api'
    ES_HOST = 'localhost:9200'
    REDIS_HOST = '127.0.0.1'
    REDIS_PORT = '6379'
    REDIS_PREFIX_USER_JOB = 'codeflares:user:job'
    REDIS_PREFIX_USER_PENDING_JOB = 'codeflares:user:job:pending'
    REDIS_PREFIX_USER_JOB_LIMIT = 3
    REDIS_PREFIX_USER_JOB_TIMEOUT = 1440
