from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import smtplib
from tornado.template import Loader, os
from logging import Logger
from core import DataDynamo
from core.model import RootAccount


class MailPublisher(object):
    def __init__(self, logger, data, config_path):
        """
        @type data: DataDynamo
        @type logger: Logger
        """
        self.logger = logger
        self.data = data
        try:
            f = open(os.path.join(config_path, 'email.json'))
            self.config = json.load(f)
            self.logger.debug('Mail module config: {0}'.format(self.config))
        except Exception as e:
            self.logger.error('Failed to initialize mail module: {0}'.format(e))

    def send(self, gl_user, subject, template_name, params, check_accept=True):
        """

        @type gl_user: RootAccount
        """
        try:
            if check_accept:
                accept = self.data.get_terms_accept(gl_user)
                if not accept or not accept['email']:
                    self.logger.warning('Warning: Not sending email, user opt-out: {0}'.format(gl_user.Key))
                    return

            gid_info = gl_user.account.info
            if 'name' and 'email' in gid_info:
                params['name'] = gid_info['name']
                self.logger.info('Info: Emailing to [{0}], gid [{1}]...'.format(gid_info['email'], gl_user.Key))
                self._do_send(params, gid_info['email'], subject, template_name)
                self.logger.info('Info: Email to [{0}] is sent...'.format(gid_info['email']))
            else:
                self.logger.warning('Warning: Not sending email, email unknown: {0}'.format(gl_user.Key))

        except Exception as e:
            self.logger.error('Error: Exception in MailPublisher.send(): {0}'.format(e))

    def _do_send(self, params, to, subject, template_name):
        # Create message container - the correct MIME type is multipart/alternative.
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.config['from'].encode('utf-8', 'ignore')
        msg['To'] = to

        # Create the body of the message (a plain-text and an HTML version).
        loader = Loader('./templates/mail')
        text = loader.load(template_name + '.txt').generate(**params)
        html = loader.load(template_name + '.html').generate(**params)
        # Record the MIME types of both parts - text/plain and text/html.
        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')
        # Attach parts into message container.
        # According to RFC 2046, the last part of a multipart message, in this case
        # the HTML message, is best and preferred.
        msg.attach(part1)
        msg.attach(part2)

        # sendmail function takes 3 arguments: sender's address, recipient's address
        # and message to send - here it is sent as one string.
        if self.config['dummy']:
            self.logger.warning('WARNING: Not sending e-mail to {0}, subj: {1}'.format(msg['To'], subject))
        else:
            s = smtplib.SMTP(host=self.config['host'].encode('utf-8', 'ignore'), port=self.config['port'])
            s.starttls()
            s.login(self.config['login'].encode('utf-8', 'ignore'), self.config['password'].encode('utf-8', 'ignore'))
            s.sendmail(msg['From'], [msg['To'], msg['From']], msg.as_string())
            s.quit()
