import traceback

import tornado
from tornado.gen import Return
from tornado.web import HTTPError

from handlers.api.base import BaseApiHandler


class OrderApiHandler(BaseApiHandler):
    def __init__(self, application, request, **kwargs):
        super(OrderApiHandler, self).__init__(application, request, **kwargs)
        self.payments = application.payments
        self.data = application.data
        self.pool = application.pool
        self.limits = self.settings['limits']

    @tornado.gen.coroutine
    def handle_get(self, gid, gl_user, args, callback=None):
        if 'token' in args:
            result = yield self.pool.submit(self.get_client_token, gid)
        else:
            _id = yield self.pool.submit(self.payments.get_user, gid)
            if not _id:
                result = {'error': 'User not found'}
            elif 'info' in args:
                result = yield self.pool.submit(self.get_info, _id, gid)
            elif 'history' in args:
                result = yield self.pool.submit(self.get_history, _id, gid)
            else:
                result = None

        # sync
        raise Return(result)

    @tornado.gen.coroutine
    def handle_post(self, gid, gl_user, args, body, callback=None):
        _id = yield self.pool.submit(self.payments.get_user, gid)
        if not _id:
            result = {'error': 'User not found'}
        elif 'subscribe' in args:
            result = yield self.pool.submit(self.create_subscription, _id, gid, body)
        elif 'cancel' in args:
            result = yield self.pool.submit(self.cancel_subscription, _id, gid)
        else:
            result = None

        # sync
        raise Return(result)

    def get_client_token(self, gid):
        try:
            r = {
                'm': self.payments.get_merchant_id(),
                'e': self.payments.get_environment(),
                't': self.payments.get_new_client_token()
            }
            self.logger.info('Created token for gid [{0}]'.format(gid))
            return r
        except Exception as e:
            self.logger.exception('ERROR: Exception in get_client_token(), {0}, {1}'.format(e, traceback.format_exc()))
            raise HTTPError(500)

    def get_info(self, _id, gid):
        return {
            '_id': _id,
            'p': self.payments.get_user_plan(_id),
            's': self.payments.get_user_subscription(_id),
            'plans': self.get_all_plans()
        }

    def get_history(self, _id, gid):
        return {'h': self.payments.get_transaction_log(_id)}

    def get_all_plans(self):
        return self.payments.get_all_plans()

    def create_subscription(self, _id, gid, body):
        try:
            plan = body['plan']
            nonce = body['nonce']
            device_data = body['dd'] if 'dd' in body else None
            # cancel existing subscription if any
            if not self._cancel_subscription(_id, gid):
                return {'error': 'Failed to cancel existing user subscription. Please email support.'}

            r = self.payments.create_user_subscription(_id, gid, plan, nonce, device_data)
            if type(r) is bool and r:
                # set limits to the plan
                if plan in self.limits:
                    self.data.set_limits(gid, self.limits[plan]['tag'])
                else:
                    self.data.set_limits(gid, self.limits['unlimited']['tag'])
                    self.logger.error('ERROR: PLAN NOT FOUND IN LIMITS [{0}]'.format(plan))

            return r

        except Exception as e:
            self.logger.exception('ERROR: Exception in create_subscription(), {0}, {1}'.format(e, traceback.format_exc()))
            raise HTTPError(500)

    def cancel_subscription(self, _id, gid):
        try:
            if not self._cancel_subscription(_id, gid):
                return {'error': 'Failed to cancel user subscription. Please email support.'}
            # drop limits to free plan
            self.data.set_limits(gid, self.limits['free']['tag'])
            return True
        except Exception as e:
            self.logger.exception('ERROR: Exception in cancel_subscription(), {0}, {1}'.format(e, traceback.format_exc()))
            raise HTTPError(500)

    def _cancel_subscription(self, _id, gid):
        self.logger.info('Deleting customer, uid [{0}], gid [{1}]'.format(_id, gid))
        result = self.payments.cancel_user_subscription(_id)
        if result:
            self.logger.info('SUCCESS: User ID [{0}], gid [{1}] deleted.'.format(_id, gid))
        else:
            self.logger.error('ERROR: Failed to delete user ID [{0}], gid [{1}].'.format(_id, gid))

        return result