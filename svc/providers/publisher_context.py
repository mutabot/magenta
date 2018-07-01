from core.model import RootAccount, SocialAccount, Link


class PublisherContext(object):
    root = None     # type: RootAccount
    source = None   # type: SocialAccount
    target = None   # type: SocialAccount
    link = None     # type: Link
