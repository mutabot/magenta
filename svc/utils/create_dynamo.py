from decimal import Decimal

import boto3
import time

dynamodb = boto3.resource('dynamodb',
                          region_name='us-west-2',
                          endpoint_url="http://localhost:9000",
                          aws_access_key_id='foo',
                          aws_secret_access_key='bar'
                          )
#table = dynamodb.Table('GidSet')


table = dynamodb.create_table(
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


with table.batch_writer() as batch:
    for i in range(150):
        stamp = Decimal(time.time() - i)
        batch.put_item(
            Item={
                'gid': '123456789000' + str(i),
                'active': 'true',
                'refreshStamp': stamp,
            }
        )
