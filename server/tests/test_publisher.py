import unittest
import logging
from mock import patch
from core import Data
from core.filter import FilterData

from providers.publisher_base import PublisherBase


class TestPublisher(PublisherBase):

    def __init__(self, log, data, config_path, picasa):
        """
        @type data: Data
        @type log: Logger
        """
        PublisherBase.__init__(self, 'twitter', log, data, config_path, picasa=picasa)


class TestPublisherBase(unittest.TestCase):
    @patch('core.Data')
    @patch('providers.Picasa')
    def setUp(self, data, picasa):
        logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
        logger = logging.getLogger(__name__)
        logger.level = logging.NOTSET
        self.publisher = TestPublisher(log=logger, data=data, config_path='', picasa=picasa)

    def test_filter_negative_only(self):
        f = {
            FilterData.keyword_kind: u'-#video,-#audio',
            FilterData.likes_kind: None,
            FilterData.strip_kind: False
        }
        item = {
            'annotation': u'This is some annotation and it is filtered out #video'
        }
        result = self.publisher.is_filter_rejected(f_ltr=f, item=item)
        self.assertTrue(result)

        item = {
            'annotation': u'No k-words in this annotation'
        }
        result = self.publisher.is_filter_rejected(f_ltr=f, item=item)
        self.assertFalse(result)

    def test_filter_positive_only(self):
        f = {
            FilterData.keyword_kind: u'#video,#audio',
            FilterData.likes_kind: None,
            FilterData.strip_kind: False
        }
        item = {
            'annotation': u'This annotation #video goes in!'
        }
        result = self.publisher.is_filter_rejected(f_ltr=f, item=item)
        self.assertFalse(result)

        item = {
            'annotation': u'No k-words in this annotation'
        }
        result = self.publisher.is_filter_rejected(f_ltr=f, item=item)
        self.assertTrue(result)

    def test_filter_mixed_only(self):
        f = {
            FilterData.keyword_kind: u'#video,-#audio',
            FilterData.likes_kind: None,
            FilterData.strip_kind: False
        }
        item = {
            'annotation': u'This annotation #video goes in!'
        }
        result = self.publisher.is_filter_rejected(f_ltr=f, item=item)
        self.assertFalse(result)

        item = {
            'annotation': u'No k-words in this annotation'
        }
        result = self.publisher.is_filter_rejected(f_ltr=f, item=item)
        self.assertTrue(result)

        item = {
            'annotation': u'Negative k-word in this annotation #audio'
        }
        result = self.publisher.is_filter_rejected(f_ltr=f, item=item)
        self.assertTrue(result)

        item = {
            'annotation': u'Both k-word in this annotation #audio #video'
        }
        result = self.publisher.is_filter_rejected(f_ltr=f, item=item)
        self.assertTrue(result)

if __name__ == '__main__':
    unittest.main()
