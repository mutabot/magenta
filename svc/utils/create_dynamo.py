import boto3
import logging

# session = boto3.Session(profile_name='magenta-service-user')
# dynamodb = session.client('dynamodb', region_name='us-west-2')


class DataDynamoCreate(object):

    # table = dynamodb.Table('GidSet')
    reset = True
	
    def __init__(self, logger, prod=False):
        self.logger = logger
			
		if prod:
			self.table_prefix = 'PROD__'
			self.session = boto3.Session()		
			self.dynamodb = session.client('dynamodb')
		else:
			self.table_prefix = 'DEV__'
			self.session = boto3.Session(profile_name='test')		
			self.dynamodb = session.client('dynamodb', endpoint_url='http://127.0.0.1:9000?region=us-east-1',  region_name='us-east-1')

    def get_table_name(self, name):
        return self.table_prefix + name

    def delete_table(self, name):
        local_table_name = self.get_table_name(name)
        try:
            self.dynamodb.delete_table(TableName=local_table_name)
        except Exception as ex:
            self.logger.info("Can't delete table {0}, {1}".format(local_table_name, ex.message))

    def create_simple_table(self, name):
        local_table_name = self.get_table_name(name)
        try:
            self.dynamodb.create_table(
                TableName=local_table_name,
                KeySchema=[
                    {
                        'AttributeName': 'AccountKey',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'Key',
                        'KeyType': 'RANGE'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'AccountKey',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'Key',
                        'AttributeType': 'S'
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            )
        except Exception as ex:
            self.logger.info("Create table: {0}".format(ex.message))

    def create_poll_table(self, name):
        local_table_name = self.get_table_name(name)
        try:
            self.dynamodb.create_table(
                TableName=local_table_name,
                KeySchema=[
                    {
                        'AttributeName': 'AccountKey',
                        'KeyType': 'HASH'  # Partition key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'AccountKey',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'Active',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'Expires',
                        'AttributeType': 'N'
                    }
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'PollIndex',
                        'KeySchema': [
                            {
                                'AttributeName': 'Active',
                                'KeyType': 'HASH'  # Partition key
                            },
                            {
                                'AttributeName': "Expires",
                                'KeyType': "RANGE"
                            }
                        ],
                        'Projection': {
                            'ProjectionType': "INCLUDE",
                            'NonKeyAttributes': ["AccountKey", "ActivityMap", "Updated"]
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
            self.logger.info("Create table: {0}".format(ex.message))

    def list_tables(self):
        resp = self.dynamodb.list_tables()
        for t in resp['TableNames']:
            self.logger.info(t)

    def create(self, reset):

        simple_tables = ['Logs', 'Accounts', 'Links']
        poll_tables = ['GidSet']

        if reset:
            for table_name in simple_tables:
                self.delete_table(table_name)
            for table_name in poll_tables:
                self.delete_table(table_name)

        for table_name in simple_tables:
            self.create_simple_table(table_name)

        for table_name in poll_tables:
            self.create_poll_table(table_name)

        self.list_tables()

		
if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
    logger = logging.getLogger('migrateLogger')
    logger.level = logging.DEBUG

    # reset dynamo tables
    logger.info('Resetting Dynamo tables...')

    creator = DataDynamoCreate(logger, True)
    creator.create(True)
