import unittest
import logging
from mock import patch
from core import Data
from core.filter import FilterData

from providers.publisher_base import PublisherBase


class TestDataApiBase(unittest.TestCase):
    @patch('redis.Redis')
    def setUp(self, rc):
        logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
        logger = logging.getLogger(__name__)
        logger.level = logging.NOTSET
        self.filter_data = FilterData(rc)

    def test_keyword_merge_none_1(self):
        filter_a = {
            FilterData.keyword_kind: u'-#video,-#audio',
            FilterData.likes_kind: None,
            FilterData.strip_kind: False
        }

        filter_b = {
            FilterData.keyword_kind: None,
            FilterData.likes_kind: None,
            FilterData.strip_kind: False
        }

        merged = FilterData.merge_filter_data(filter_a, filter_b, included={FilterData.keyword_kind, FilterData.keyword_merge})

        self.assertEquals(merged[FilterData.keyword_kind], u'-#video,-#audio')

    def test_keyword_merge_none_2(self):
        filter_a = {
            FilterData.keyword_kind: None,
            FilterData.likes_kind: None,
            FilterData.strip_kind: False
        }

        filter_b = {
            FilterData.keyword_kind: None,
            FilterData.likes_kind: None,
            FilterData.strip_kind: False
        }

        merged = FilterData.merge_filter_data(filter_a, filter_b, included={FilterData.keyword_kind, FilterData.keyword_merge})

        self.assertEquals(merged[FilterData.keyword_kind], u'')

    def test_keyword_merge_none_3(self):
        filter_a = {
            FilterData.keyword_kind: None,
            FilterData.likes_kind: None,
            FilterData.strip_kind: False
        }

        filter_b = {
            FilterData.keyword_kind: u'-#video,-#audio',
            FilterData.likes_kind: None,
            FilterData.strip_kind: False
        }

        merged = FilterData.merge_filter_data(filter_a, filter_b, included={FilterData.keyword_kind, FilterData.keyword_merge})

        self.assertEquals(merged[FilterData.keyword_kind], u'-#video,-#audio')

if __name__ == '__main__':
    unittest.main()
