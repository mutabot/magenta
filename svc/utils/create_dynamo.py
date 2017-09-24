from decimal import Decimal

import boto3
import time

# session = boto3.Session(profile_name='magenta-service-user')
# dynamodb = session.client('dynamodb', region_name='us-west-2')

session = boto3.Session(profile_name='test')
dynamodb = session.client('dynamodb', endpoint_url='http://127.0.0.1:9000?region=us-east-1',  region_name='us-east-1')

# table = dynamodb.Table('GidSet')

table_prefix = 'DEV__'
reset = True


def get_table_name(name):
    return table_prefix + name


def delete_table(name):
    local_table_name = get_table_name(name)
    try:
        dynamodb.delete_table(TableName=local_table_name)
    except Exception as ex:
        print "Can't delete table {0}, {1}".format(local_table_name, ex.message)


def create_simple_table(name):
    local_table_name = get_table_name(name)
    try:
        dynamodb.create_table(
            TableName=local_table_name,
            KeySchema=[
                {
                    'AttributeName': 'gid',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'key',
                    'KeyType': 'RANGE'  # Partition key
                },
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'gid',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'key',
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
    except Exception as ex:
        print "Create table: {0}".format(ex.message)


def create_poll_table(name):
    local_table_name = get_table_name(name)
    try:
        dynamodb.create_table(
            TableName=local_table_name,
            KeySchema=[
                {
                    'AttributeName': 'gid',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'gid',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'active',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'refreshStamp',
                    'AttributeType': 'N'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'PollIndex',
                    'KeySchema': [
                        {
                            'AttributeName': 'active',
                            'KeyType': 'HASH'  # Partition key
                        },
                        {
                            'AttributeName': "updated",
                            'KeyType': "RANGE"
                        }
                    ],
                    'Projection': {
                        'ProjectionType': "INCLUDE",
                        'NonKeyAttributes': ["gid"]
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 1
                    }
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
    except Exception as ex:
        print "Create table: {0}".format(ex.message)

def list_tables():
    resp = dynamodb.list_tables()
    for t in resp['TableNames']:
        print t

if __name__ == '__main__':

    simple_tables = ['Logs', 'Accounts', 'Links']
    poll_tables = ['GidSet']

    if reset:
        for table_name in simple_tables:
            delete_table(table_name)
        for table_name in poll_tables:
            delete_table(table_name)

    for table_name in simple_tables:
        create_simple_table(table_name)

    for table_name in poll_tables:
        create_poll_table(table_name)

    list_tables()
