import logging
import unittest

import mock

from providers.bitly_short import BitlyShorten


class IntegrationTestShortnerBase(unittest.TestCase):
    @mock.patch('redis.Redis')
    def setUp(self, rc):
        self.config_path = '../etc/conf/iris'
        logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
        logger = logging.getLogger(__name__)
        logger.level = logging.NOTSET
        self.shortner = BitlyShorten(logger, config_path=self.config_path)

    def test_shorten(self):

        short = self.shortner.get_short_url('https://magentariver.com')

        self.assertIsNotNone(short)


if __name__ == '__main__':

    # dir_path = os.path.dirname(os.path.realpath(__file__))

    unittest.main()
