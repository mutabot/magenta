from decimal import Decimal

import boto3
import time

dynamodb = boto3.resource('dynamodb',
                          region_name='us-east-1',
                          endpoint_url="http://localhost:9000",
                          aws_access_key_id='foo',
                          aws_secret_access_key='bar'
                          )
#table = dynamodb.Table('GidSet')


try:
    table_GidLog = dynamodb.create_table(
        TableName='GidLog',
        KeySchema=[
            {
                'AttributeName': 'gid',
                'KeyType': 'HASH'  #Partition key
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'gid',
                'AttributeType': 'S'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 10,
            'WriteCapacityUnits': 10
        }
    )
except:
    print "Table GidLog"

try:
    table_GidSet = dynamodb.create_table(
        TableName='GidSet',
        KeySchema=[
            {
                'AttributeName': 'gid',
                'KeyType': 'HASH'  #Partition key
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
                        'KeyType': 'HASH'  #Partition key
                    },
                    {
                        'AttributeName': "refreshStamp",
                        'KeyType': "RANGE"
                    }
                ],
                'Projection': {
                    'ProjectionType': 'KEYS_ONLY'
                },
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 10,
                    'WriteCapacityUnits': 1
                }
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 10,
            'WriteCapacityUnits': 10
        }
    )
except:
    print "Table GidSet"
