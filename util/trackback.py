# -*- coding: utf-8 -*-
# Copyright (c) <2008-2009> pizzamx <pizzamx@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from google.appengine.ext import webapp
from google.appengine.ext.db import BadValueError
from model import Post, Comment

import logging, urllib
from xmlrpclib import ServerProxy, Error

class TrackbackHandler(webapp.RequestHandler):
    def post(self, y, m, slug):
        logging.debug(self.request.body)
        post = Post.get_by_id('_' + slug)
        self.response.headers.add_header('Content-type', 'text/xml')
        
        tb = Comment()
        tb.isTrackback = True
        tb.post = post.key
        tb.title = urllib.unquote(self.request.get('title'))
        tb.content = urllib.unquote(self.request.get('excerpt'))
        try:
            tb.url = urllib.unquote(self.request.get('url'))
        except BadValueError:
            self.response.out.write('''
                <?xml version="1.0" encoding="utf-8"?>
                <response>
                    <error>1</error>
                    <message>Malformed URL</message>
                </response>
            ''')
            return
        tb.authorName = urllib.unquote(self.request.get('blog_name'))
        tb.authorEmail = 'test@example.com' #TODO: better one?
        tb.ip = self.request.remote_addr
        #5/25/14: 暂时停止接收！
        #tb.put()

        self.response.out.write('''
            <?xml version="1.0" encoding="utf-8"?>
            <response>
                <error>0</error>
            </response>
        ''')

