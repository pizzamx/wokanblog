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

import webapp2

from post import post_query, archive_query
from util import trackback, theme

application = webapp2.WSGIApplication([
    ('/', post_query.Index),
    (r'/page/(\d*)', post_query.Index),
    (r'/img/([^/]+)/?', post_query.ServeImage),
    ('/(comments/)?feed', post_query.Feed),
    (r'/tag/(.*?)/page/(\d*)', archive_query.TagArchive),
    (r'/tag/([^/]+)/?', archive_query.TagArchive),
    (r'/theme/(.*?)/(.*?)', theme.SetTheme),
    (r'/(\d{4})/(?:(\d{1,2})/)?(?:(\d{1,2})/)?(?:page/(\d*))?', archive_query.DateRangeArchive),
    (r'/(\d{4})/(\d{1,2})/([^/]+)/?', post_query.Single),
    (r'/(\d{4})/(\d{2})/(.*?)/trackback', trackback.TrackbackHandler),
    (r'/(.*)', post_query.Page)
], debug=False)
