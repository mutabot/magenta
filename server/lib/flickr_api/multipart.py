"""
    Deals with multipart POST requests.

    The code is adapted from the recipe found at :
    http://code.activestate.com/recipes/146306/
    No author name was given.

    Author : Alexis Mignon (c)
    email  : alexis.mignon@gmail.Com
    Date   : 06/08/2011

"""

import httplib
import mimetypes
import tempfile
import urlparse
import requests


def posturl(url, fields, files):
    urlparts = urlparse.urlsplit(url)
    return post_multipart_ex(urlparts[1], urlparts[2], fields, files)


def post_multipart(host, selector, fields, files):
    """
    Post fields and files to an http host as multipart/form-data.
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be
    uploaded as files.

    Return the server's response page.
    """
    content_type, body = encode_multipart_formdata(fields, files)
    h = httplib.HTTPConnection(host)
    headers = {"Content-Type": content_type, 'content-length': str(len(body))}
    h.request("POST", selector, headers=headers)
    h.send(body)

    r = h.getresponse()
    data = r.read()
    h.close()
    return r, data


def encode_multipart_formdata(fields, files):
    """
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be
    uploaded as files.

    Return (content_type, body) ready for httplib.HTTP instance
    """
    BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
    CRLF = '\r\n'
    L = []
    for (key, value) in fields:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"' % key)
        L.append('')
        L.append(value)
    for (key, filename, value) in files:
        filename = filename.encode("utf8")
        L.append('--' + BOUNDARY)
        L.append(
            'Content-Disposition: form-data; name="%s"; filename="%s"' % (
                key, filename
            )
        )
        L.append('Content-Type: %s' % get_content_type(filename))
        L.append('')
        L.append(value)
    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY

    return content_type, body


def post_multipart_ex(host, selector, fields, files):
    """
    Post fields and files to an http host as multipart/form-data.
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be
    uploaded as files.

    Return the server's response page.
    """
    CRLF = '\r\n'
    BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
    TRAILER = CRLF + '--' + BOUNDARY + '--' + CRLF

    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY

    h = httplib.HTTPSConnection(host)
    param_length = 0
    params_body = ''
    L = []
    for (key, value) in fields:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"' % key)
        L.append('')
        L.append(value)

    params_body += CRLF.join(L)
    params_body += CRLF

    file_heads = {}
    for (name, f, size) in files:
        L = [
            '--' + BOUNDARY,
            'Content-Disposition: form-data; name="%s"; filename="%s"' % ('photo', name),
            'Content-Type: %s' % get_content_type(name),
            '',
            ''
        ]
        file_heads[name] = (CRLF.join(L), f, size)

    headers = {
        "Content-Type": content_type,
        'Content-Length': str(len(params_body) + sum([size + len(head) for name, (head, _, size) in file_heads.iteritems()]) + len(TRAILER))
    }

    h.request("POST", selector, headers=headers)

    h.send(params_body)

    for _, (head, f, size) in file_heads.iteritems():
        h.send(head)

        while True:
            buffer = f.read(8192)
            if not buffer:
                break

            h.send(buffer)

    h.send(TRAILER)

    r = h.getresponse()
    data = r.read()
    h.close()
    return r, data


def get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'
