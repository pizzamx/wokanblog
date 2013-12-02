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
from google.appengine.api import memcache

from util import feedparser
from model import Blogroll

from datetime import datetime

import logging, time, re

_my_date_pattern = re.compile(ur'(\d+)年(\d+)月(\d+)日\D+(\d+):(\d+)')

#傻叉百度rss，居然用这么恶心的格式
def myDateHandler(aDateString):
    month, day, year, hour, minute, second = _my_date_pattern.search(aDateString).groups()
    return (int(year), int(month), int(day), int(hour), int(minute), 0, 0, 0, 0)

feedparser.registerDateHandler(myDateHandler)

class UpdateblogrollCronJob(webapp.RequestHandler):
    def get(self):
        batch_size = 3

        start = memcache.get('blogroll_update_start')
        if not start:
            start = 0
            
        brs = Blogroll.all().fetch(batch_size, start)
        start += batch_size
            
        if start >= Blogroll.all().count():
            start = 0
            
        memcache.set('blogroll_update_start', start)
        
        for br in brs:
            try:
                d = feedparser.parse(br.feedUrl)
                entry = d.entries[0]
                title = entry.title
                pubDate = entry.date_parsed
                if title is not None and title != br.lastTitle:
                    diff = -1
                    #logging.debug('%s updated' % br.feedUrl)
                    d = datetime.fromtimestamp(time.mktime(pubDate))    #还是不考虑时区了，麻烦
                    diff = datetime.now().toordinal() - d.toordinal()
                    
                    br.lastUpdate = d
                    br.lastTitle = title
                    br.put()
            except Exception, e:
                logging.debug('Error occurred whild reading %s: %s' % (br.feedUrl, e))
