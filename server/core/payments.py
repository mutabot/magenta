import json
import time
import random
import string
import traceback
import braintree
from braintree.environment import Environment

from core.data_base import DataBase
import utils


class Payments(DataBase):
    """
    Static definitions of keys used by Payments
    """
    KEY_ID2GID = 'PTS_ID2GID'
    KEY_GID2ID = 'PTS_GID2ID'
    KEY_PLAN = 'plan'
    KEY_ALL_PLANS = 'all_plans'
    KEY_SUBSCRIPTION = 'sub'
    KEY_GID = 'gid'
    KEY_DELETED = 'del'
    KEY_FMT_LOG = '{0}:log'
    MAX_LOG_COUNT = 99

    LOG_MESSAGE_FORMAT = {
        'NEW_ID': 'Account created. ID: {1}, Google ID: {0}.',
        'PLAN': 'Plan changed to: {0}.',
        'SUB': 'Payment accepted. Transaction ID: {0}.',
        'SUB_CAN': 'Subscription cancelled.',
        'DEL_ID': 'Account deleted.'
    }

    ENVIRONMENT_NAME_MAP = {
        Environment.Production.server_and_port: 'P',
        Environment.Sandbox.server_and_port: 'S',
    }

    def __init__(self, logger, data, redis_host, redis_port, redis_db):
        super(Payments, self).__init__(logger, redis_host, redis_port, redis_db)
        random.seed(time.time())
        self.data = data

    def get_user(self, gid):
        _id = self.rc.hget(self.KEY_GID2ID, gid)
        if not _id:
            while True:
                _id = self.get_id()
                if self.rc.hsetnx(_id, self.KEY_GID, gid):
                    break

            self.logger.info('Generated UID [{0}] for GID [{1}]'.format(_id, gid))
            if not self.rc.hsetnx(self.KEY_GID2ID, gid, _id):
                self.logger.error('ERROR: GID already bound to UID: [{0}] <-> [{1}]'.format(gid, _id))
                return None

            self.add_transaction_log(_id, ['NEW_ID', gid, _id])

        return _id

    def delete_user(self, gid):
        """
        Deletes a user. All subscriptions will be cancelled and all user data removed.
        @param gid:
        @return:
        """
        _id = self.rc.hget(self.KEY_GID2ID, gid)
        if not _id:
            self.logger.info("payments.delete_user(): No user for GID [{0}]".format(gid))
            return True

        if not self.cancel_user_subscription(_id):
            self.logger.error("ERROR: payments.delete_user(): Could not delete user GID [{0}]".format(gid))
            return False

        # set the deleted flag to a user
        self.add_transaction_log(_id, ['DEL_ID'])

    def set_user_plan(self, _id, plan):
        old_plan = self.rc.hget(_id, self.KEY_PLAN)
        self.rc.hset(_id, self.KEY_PLAN, plan)
        self.add_transaction_log(_id, ['PLAN', plan, old_plan])
        return _id

    def get_user_plan(self, _id):
        return self.rc.hget(_id, self.KEY_PLAN)

    def set_user_subscription(self, _id, sub_id):
        self.rc.hset(_id, self.KEY_SUBSCRIPTION, sub_id)
        self.add_transaction_log(_id, ['SUB', sub_id])
        return _id

    def update_customer_info(self, customer, gid):
        try:
            gid_info = self.data.get_gid_info(gid)
            if gid_info:
                customer.update({
                    'first_name': gid_info['given_name'] if 'given_name' in gid_info else '',
                    'last_name': gid_info['family_name'] if 'family_name' in gid_info else '',
                    'email': gid_info['email'] if 'email' in gid_info else 'noemail@magentariver.com',
                })
        except Exception as ex:
            self.logger.error('EXCEPTION: Getting user details for gid: {0}, {1}, {2}'.format(gid, ex, traceback.format_exc()))

    def create_user_subscription(self, _id, gid, plan, nonce, device_data=None):
        # create brand new customer
        self.logger.info('Creating user, ID [{0}], gid [{1}] to [{2}]'.format(_id, gid, plan))
        customer = {
            'id': _id,
            'fax': gid,
            'payment_method_nonce': nonce,
            'device_data': device_data
        }
        # populate optional customer records from the master DB
        self.update_customer_info(customer, gid)

        # invoke web-request
        result = braintree.Customer.create(customer)

        if not (result and result.is_success and result.customer):
            self.logger.error('ERROR: Failed to create customer ID [{0}], gid [{1}]'.format(_id, gid))
            return {'error': 'Failed to process payment. Payment system message: {0}'.format(result.message)}

        # get customer from result
        customer = result.customer

        # collect token
        self.logger.info('Collecting token..., ID [{0}]...'.format(_id))
        if len(customer.credit_cards):
            token = customer.credit_cards[0].token
        else:
            token = customer.paypal_accounts[0].token

        self.logger.info('Subscribing user, ID [{0}], gid [{1}] to [{2}]'.format(_id, gid, plan))
        result = braintree.Subscription.create({
            'plan_id': plan,
            'payment_method_token': token
        })

        if not result.is_success:
            self.cancel_user_subscription(_id)
            self.logger.error('ERROR: Filed to subscribe user ID [{0}], {1}'.format(_id, result.message))
            return {'error': 'Failed to subscribe user'}

        self.set_user_plan(_id, plan)
        self.set_user_subscription(_id, result.subscription.id)

        self.logger.info('SUCCESS: User ID [{0}], gid [{1}] subscribed to [{2}].'.format(_id, gid, plan))

        return True

    def cancel_user_subscription(self, _id):
        # check if this is existing customer
        plan = self.get_user_plan(_id)
        sub_id = self.get_user_subscription(_id)
        self.logger.info('Deleting customer, uid [{0}], plan [{1}], sub_id [{2}]'.format(_id, plan, sub_id))
        try:
            result = braintree.Customer.find(_id)
            if result:
                self.logger.info('INFO: Found customer ID [{0}], fax [{1}], cards [{2}]'.format(_id, result.fax, len(result.credit_cards)))
                if not (plan or sub_id):
                    self.logger.error('ERROR: ******** ID [{0}] exists but no subscription!'.format(_id))

                result = braintree.Customer.delete(_id)
                # deletion of the customer will remove all subscriptions and credit cards
                if not result.is_success:
                    self.logger.error('ERROR: Filed to delete user ID [{0}], {1}'.format(_id, result.message))
                    return False
            else:
                self.logger.warning('WARNING: Customer ID [{0}] not found, {1}'.format(_id, result.message))
        except Exception as e:
            self.logger.warning('WARNING: Customer ID [{0}] not found, {1}'.format(_id, e))

        self.rc.hdel(_id, self.KEY_SUBSCRIPTION)
        self.rc.hdel(_id, self.KEY_PLAN)
        self.add_transaction_log(_id, ['SUB_CAN'])
        self.logger.info('SUCCESS: User uid [{0}] deleted.'.format(_id))
        return True

    def get_user_subscription(self, _id):
        return self.rc.hget(_id, self.KEY_SUBSCRIPTION)

    def add_transaction_log(self, _id, message):
        rec = {time.time(): message}
        key = self.KEY_FMT_LOG.format(_id)
        self.rc.lpush(key, json.dumps(rec))
        self.rc.ltrim(key, 0, self.MAX_LOG_COUNT)

    def get_transaction_log(self, _id):
        try:
            log = self.rc.lrange(self.KEY_FMT_LOG.format(_id), 0, -1)
            if not log:
                return []
            result = [{'t': t, 'm': self.format_message(m[0], m[1:])} for v in log for t, m in json.loads(v).iteritems()]
            return result
        except Exception as e:
            self.logger.error('ERROR: Exception in : get_transaction_log, {0}'.format(e))
            return None

    def get_all_plans(self):
        try:
            plans = self.rc.hgetall(self.KEY_ALL_PLANS)
            return [json.loads(p) for p in plans.itervalues()]
        except Exception as e:
            self.logger.error('ERROR: Filed to get all plans, {0}'.format(e))
            return []

    def initialize(self, config_path):
        self.logger.info('INFO: payments: Initializing...')
        # configure braintree
        env_map = {
            'sandbox': Environment.Sandbox,
            'production': Environment.Production
        }
        cfg = utils.config.load_config(config_path, 'braintree_credentials.json')
        braintree.Configuration.configure(env_map[cfg['environment']],
                                          merchant_id=cfg['merchant_id'],
                                          public_key=cfg['public_key'],
                                          private_key=cfg['private_key'])
        # preload plans
        try:
            result = braintree.Plan.all()
            plans = [{
                'id': p.id,
                'name': p.name,
                'price': p.price,
                'ccy': p.currency_iso_code,
                'description': p.description
            } for p in result]

            self.logger.info('INFO: payments: Caching [{0}] plans'.format(len(plans)))

            self.rc.delete(self.KEY_ALL_PLANS)
            for plan in plans:
                self.rc.hset(self.KEY_ALL_PLANS, plan['id'], json.dumps(plan))

        except Exception as e:
            self.logger.error('ERROR: payments: Filed to initialize, {0}'.format(e))

    @staticmethod
    def get_merchant_id():
        return braintree.Configuration.merchant_id

    @staticmethod
    def get_environment():
        try:
            return Payments.ENVIRONMENT_NAME_MAP[braintree.Configuration.environment.server_and_port]
        except:
            return None

    @staticmethod
    def get_new_client_token():
        return braintree.ClientToken.generate()

    @staticmethod
    def format_message(key, args):
        try:
            f = Payments.LOG_MESSAGE_FORMAT[key]
            return f.format(*args)
        except:
            return None

    @staticmethod
    def get_id():
        return 'II{0}{1}{2}'.format(
            ''.join(random.choice(string.digits) for i in range(0, 3)),
            ''.join(random.choice(string.uppercase) for i in range(0, 2)),
            ''.join(random.choice(string.digits) for i in range(0, 4)))