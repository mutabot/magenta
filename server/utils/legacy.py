from core import data


def get_data(logger, redis_host, redis_port, redis_db):
    return data.Data(logger, redis_host, redis_port, redis_db)