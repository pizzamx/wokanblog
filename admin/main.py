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

from admin import post_update
from admin import comment_update
from admin.cronjobs import UpdateblogrollCronJob, DSCronJob

import util, widget, logging

application = webapp2.WSGIApplication([
    ('/admin/', post_update.NewPost),
    ('/admin/write', post_update.NewPost),
    ('/admin/uploadImg', post_update.NewImg),
    (r'/(?:(\d{4})/)?(?:(\d{1,2})/)?([^/]+)/edit/?', post_update.Edit),
    ('/admin/updateblogroll', UpdateblogrollCronJob),
    ('/admin/exe_ds_task', DSCronJob),
    ('/admin/comments/(?:page/(\d+))?', comment_update.ListComments),
    ('/admin/comments/report/(.*)', comment_update.ReportSpam),
    ('/admin/comments/markham/(.*)', comment_update.MarkHam),
    (r'/comment/(.*)', comment_update.NewComment)
], debug=True)
