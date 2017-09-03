import json
from decimal import Decimal

import boto3
import time

import jsonpickle
from boto3.dynamodb.conditions import Key

from core import provider_dynamo
from core.data_base import DataBase
from core.data_interface import DataInterface
from core.model.schema2 import S2
from providers.google_rss import GoogleRSS


class DataDynamo(DataBase, DataInterface):

    def commit_pid_records(self, root_pid):
        pass

    def cache_pid_records(self, root_pid):
        pass

    def get_accounts(self, root_pid, accounts):
        pass

    def add_log(self, gid, message):
        pass

    def set_links(self, root_pid, links):
        pass

    def flush(self, root_pid):
        pass

    def set_model_document(self, document_name, root_pid, items):
        key_name = S2.document_key_name(root_pid, document_name)
        self.rc.delete(key_name)
        for item in items:
            js = jsonpickle.dumps(item)
            self.rc.hset(key_name, item.key, js)

    def get_log(self, root_pid):
        key_name = S2.document_key_name(root_pid, "logs")
        log_raw = self.rc.hgetall(key_name)
        result = {key: json.loads(value)["Items"] for key, value in log_raw.iteritems()}
        return result

    def set_log(self, root_pid, log):
        key_name = S2.document_key_name(root_pid, "logs")
        self.rc.delete(key_name)
        for key, value in log.iteritems():
            self.rc.hset(key_name, key, json.dumps({"Items": value}))

    def __init__(self, logger, dynoris_url, redis_connection):
        DataInterface.__init__(self)
        DataBase.__init__(self,
                          logger,
                          redis_connection['host'],
                          redis_connection['port'],
                          redis_connection['db'])

        self.logger = logger
        self.dynoris_url = dynoris_url
        #session = boto3.Session(
        #    profile_name=dynamo_connection['profile_name']
        #)
        #self.dynamo_db = session.client(
        #    'dynamodb',
        #    endpoint_url=dynamo_connection['endpoint_url'],
        #    region_name=dynamo_connection['region_name']
        #)

        self.poll_table_name = 'GidSet'
        self.poll_table_index_name = 'PollIndex'

        self.provider = {
            'facebook': provider_dynamo.ProviderDynamo(self.rc, 'facebook'),
            'twitter': provider_dynamo.ProviderDynamo(self.rc, 'twitter'),
            'tumblr': provider_dynamo.ProviderDynamo(self.rc, 'tumblr'),
            'flickr': provider_dynamo.ProviderDynamo(self.rc, 'flickr'),
            '500px': provider_dynamo.ProviderDynamo(self.rc, '500px'),
            'linkedin': provider_dynamo.ProviderDynamo(self.drc, 'linkedin'),
        }

    def unregister_gid(self, gid):
        pass

    def remove_from_poller(self, gid):
        pass

    def is_loading(self):
        pass

    def register_gid(self, gid):
        stamp = Decimal(time.time())
        self.dynamo_db.put_item(
            TableName=self.poll_table_name,
            Item={
                'gid': gid,
                'active': 'true',
                'refreshStamp': stamp,
            }
        )

    def poll(self, refresh_stamp):
        return self.dynamo_db.query(
            TableName=self.poll_table_name,
            IndexName=self.poll_table_index_name,
            Limit=1,
            KeyConditionExpression=Key('active').eq('true') & Key('refreshStamp').lt(refresh_stamp)
        )

    def cache_activities_doc(self, gid, activities_doc, collision_window=0.0):
        now = time.time()
        try:
            cached = self.dynamo_db.update_item(
                TableName=self.poll_table_name,
                Key={'gid': gid},
                UpdateExpression='SET refreshStamp=:refreshStamp, cacheGoogle=:cacheGoogle',
                ConditionExpression='refreshStamp < :refreshThreshold',
                ExpressionAttributeValues={
                    ':refreshStamp': Decimal(now),
                    ':refreshThreshold': Decimal(now - collision_window),
                    ':cacheGoogle': json.dumps(activities_doc, ensure_ascii=False)
                },
                ReturnValues='ALL_OLD'
            )
            # compare etags
            # TODO: Google specific
            attributes = cached['Attributes']
            cached_item = json.loads(attributes['cacheGoogle']) if 'cacheGoogle' in attributes else None

            up_a = GoogleRSS.get_update_timestamp_iso(cached_item) if cached_item else None
            up_b = GoogleRSS.get_update_timestamp_iso(activities_doc)

            if up_a is None:
                self.logger.info('New doc {0}, {1} <- {2}'.format(gid, time.ctime(0.0), time.ctime(now)))
            elif up_a == up_b:
                self.logger.info('Same doc {0}, {1} <-> {2}'
                                 .format(gid, time.ctime(cached['Attributes']['refreshStamp']), time.ctime(now)))
            else:
                self.logger.info('Updated  {0}, {1} -> {2}'.format(gid, up_a, up_b))

            return up_a and up_a != up_b

        except Exception as ex:
            self.logger.info('Update collision {0}, {1}'.format(gid, ex.message))

    def get_activities(self, gid):
        try:
            cached = self.dynamo_db.get_item(
                TableName=self.poll_table_name,
                Key={'gid': gid}
            )
            return cached['Item'] if 'Item' in cached else None
        except Exception as ex:
            self.logger.info('Get item failed {0}:{1}'.format(gid, ex.message))

        return None

    def get_provider(self, provider_name):
        return self.provider[provider_name] if provider_name in self.provider else None

    def activities_doc_from_item(self, item):
        return item['cacheGoogle'] if 'cacheGoogle' in item else None

    def get_sources(self, gid):
        pass

    def get_linked_accounts(self, gid, temp=False):
        pass

    def scan_gid(self, page=None):
        pass
