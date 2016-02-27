import codecs
import json
import traceback
import sys
import time


class DataGrep:
    def __init__(self, log, data):
        self.data = data
        self.log = log
        sys.stdout = codecs.getwriter('utf8')(sys.stdout)
        sys.stderr = codecs.getwriter('utf8')(sys.stderr)

    def grep(self):
        lookup = {'greenbody-llc-9721@pages.plusgoogle.com', 'greenbodydeo@gmail.com'}
        gid_keys = self.data.rc.keys('gid:*')
        for gid_key in gid_keys:
            try:
                m = self.data.rc.hget(gid_key, 'info')
                info = json.loads(m)
                if info and 'email' in info:
                    if info['email'].lower() in lookup:
                        print 'GID: {0} <=> {1}'.format(gid_key, info['email'].lower())
            except Exception as e:
                self.log.error('Exception: {0}\r\n{1}'.format(e, traceback.format_exc()))

        self.log.info('All done!')

    def multiple_parents(self):
        gid_set = self.data.rc.keys('gid:*')
        hdr = 'GID, Children, DstCh, Limits,Last,Email,Name'
        print(hdr)
        self.log.info(hdr)
        self.process_gid('100179705036605636374')
        for gid_txt in gid_set:
            self.process_gid(gid_txt[4:])

    def process_gid(self, gid):
        children = self.data.get_linked_children(gid)
        dst_children = self.data.get_linked_children(gid, bag='dst')
        lmts = self.data.get_limits(gid)
        gid_info = self.data.get_gid_info(gid)
        log = self.data.get_log(gid)
        log_max_max = [(k, max(v, key=lambda record:record[1])[1]) for k, v in log.iteritems() if v]
        log_max = max(log_max_max, key=lambda record:record[1]) if log_max_max else ('', 0.0)

        msg = u'"{0}",{1},{2},{3},{4},{5},{6}'.format(gid,
                                                  len(children),
                                                  len(dst_children),
                                                  lmts,
                                                  time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(log_max[1])),
                                                  gid_info['email'] if 'email' in gid_info else '',
                                                  gid_info['name'] if 'name' in gid_info else '')
        self.log.info(msg.encode(encoding='utf-8', errors='ignore'))
        print(msg)