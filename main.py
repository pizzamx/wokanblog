# -*- coding: utf-8 -*-
# Copyright (c) <2008-2021> pizzamx <pizzamx@gmail.com>
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

import os

from flask import Flask, render_template, request
#from google.appengine.api import wrap_wsgi_app

from util import theme, trackback

from . import admin, blog

"""
    加过滤：
    post_query
        Index
        Single
        Page
        Feed
    archive_query
        TagArchive
        DateRangeArchive
application = webapp2.WSGIApplication([
    ok('/', post_query.Index),
    ok(r'/page/(next|prev)/(\S*)', post_query.Index),
    ok(r'/img/([^/]+)/?', post_query.ServeImage),
    ok('/(comments/)?feed', post_query.Feed),
    --(r'/tag/(.*?)/page/(next|prev)/(\S*)', archive_query.TagArchive),
    --(r'/tag/([^/]+)/?', archive_query.TagArchive),
    --(r'/theme/(.*?)/(.*?)', theme.SetTheme),
    --(r'/(\d{4})/(?:(\d{1,2})/)?(?:(\d{1,2})/)?(?:page/(next|prev)/(\S*))?', archive_query.DateRangeArchive),
    ok(r'/(\d{4})/(\d{1,2})/([^/]+)/?', post_query.Single),
    ok(r'/(\d{4})/(\d{2})/(.*?)/trackback', trackback.TrackbackHandler),
    ok(r'/(.*)', post_query.Page)

    ok('/admin/', post_update.NewPost),
    ok('/admin/write', post_update.NewPost),
    ok('/admin/uploadImg', post_update.NewImg),
    ok(r'/(?:(\d{4})/)?(?:(\d{1,2})/)?([^/]+)/edit/?', post_update.Edit),
    --('/admin/updateblogroll', UpdateblogrollCronJob),
    --('/admin/exe_ds_task', DSCronJob),
    --('/admin/comments/(?:page/(\d+))?', comment_update.ListComments),
    ok('/admin/comments/report/(.*)', comment_update.ReportSpam),
    ok('/admin/comments/markham/(.*)', comment_update.MarkHam),
    ok(r'/comment/(.*)', comment_update.NewComment)

], debug=False)
"""
app = Flask(__name__)
#app.wsgi_app = wrap_wsgi_app(app.wsgi_app)
app.register_blueprint(blog.bp)
app.register_blueprint(admin.bp)

# https://codelabs.developers.google.com/codelabs/cloud-gae-python-migrate-4-rundocker?hl=zh-cn#3
if __name__ == '__main__':
    app.run(debug=True, threaded=True, host='0.0.0.0',
            port=int(os.environ.get('PORT', 8080)))
