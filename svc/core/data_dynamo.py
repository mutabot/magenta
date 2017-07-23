from decimal import Decimal

import boto3
import time

from core.data_interface import DataInterface
from providers.google_rss import GoogleRSS


class DataDynamo(DataInterface):

    def __init__(self, logger, dynamo_connection):
        DataInterface.__init__(self)
        self.logger = logger
        self.dynamo_db = boto3.resource('dynamodb',
                                        region_name=dynamo_connection['region_name'],
                                        endpoint_url=dynamo_connection['endpoint_url'],
                                        aws_access_key_id=dynamo_connection['aws_access_key_id'],
                                        aws_secret_access_key=dynamo_connection['aws_secret_access_key'])

        self.table = self.dynamo_db.Table('GidSet')

    def unregister_gid(self, gid):
        pass

    def remove_from_poller(self, gid):
        pass

    def is_loading(self):
        pass

    def register_gid(self, gid):
        stamp = Decimal(time.time())
        self.table.put_item(
            Item={
                'gid': gid,
                'active': 'true',
                'refreshStamp': stamp,
            }
        )

    def cache_activities_doc(self, gid, activities_doc, collision_window=0.0):
        now = time.time()
        try:
            cached = self.table.update_item(
                Key={'gid': gid},
                UpdateExpression='SET refreshStamp=:refreshStamp, cacheGoogle=:cacheGoogle',
                ConditionExpression='refreshStamp < :refreshThreshold',
                ExpressionAttributeValues={
                    ':refreshStamp': Decimal(now),
                    ':refreshThreshold': Decimal(now - collision_window),
                    ':cacheGoogle': activities_doc
                },
                ReturnValues='ALL_OLD'
            )
            # compare etags
            # TODO: Google specific
            etag_a = GoogleRSS.get_item_etag(activities_doc)
            etag_b = GoogleRSS.get_item_etag(cached['cacheGoogle']) if 'cacheGoogle' in cached else None

            if etag_b in None:
                self.logger.info('New doc {0}, {1} <- {2}'
                                 .format(gid, time.ctime(0.0), time.ctime(now)))
            elif etag_a == etag_b:
                self.logger.info('Same doc {0}, {1} <- {2}'
                                 .format(gid, time.ctime(cached['Attributes']['refreshStamp']), time.ctime(now)))
            else:
                self.logger.info('Updated  {0}, {1} -> {2}'
                                 .format(gid, time.ctime(cached['Attributes']['refreshStamp']), time.ctime(now)))

            return etag_b and etag_a != etag_b

        except Exception as ex:
            self.logger.info('Update collision {0}:{1}'.format(gid, time.ctime(now)))

    def activities_doc_from_item(self, item):
        return item['cacheGoogle'] if 'cacheGoogle' in item else None
