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
from mako.template import Template
from mako.lookup import TemplateLookup
from model import Post, Tag

from datetime import date, datetime, timedelta

import util, widget, post_query

import os, urllib, math


class TagArchive(post_query.QueryBase):
    def get(self, tagName, drct=None, page_cursor=None):
        tagName = unicode(urllib.unquote(tagName), 'utf-8')
        tag = Tag.get_by_id('_' + tagName)
        if not tag:
            self.fof()
        else:
            posts = Post.query(Post.tags == tag.key).order(-Post.date)
            self.title = tagName
            self.dumpMultiPage(posts, drct, page_cursor, 'index.html')

class DateRangeArchive(post_query.QueryBase):
    def get(self, year, month, day, drct=None, page_cursor=None):
        year = int(year)
        if day:
            the_date = datetime(year, int(month), int(day))
            posts = Post.query(Post.isPage == False, Post.date > the_date, Post.date < the_date + timedelta(days=1))
            self.title = u'%d年%s月%s日的存档' % (year, month, day)
        elif month:
            month = int(month)
            fdnm = datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)
            posts = Post.query(Post.isPage == False, Post.date > datetime(year, month, 1), Post.date < fdnm)
            self.title = u'%d年%s月的存档' % (year, month)
        else:
            posts = Post.query(Post.isPage == False, Post.date > datetime(year, 1, 1), Post.date <  datetime(year + 1, 1, 1))
            self.title = u'%d年的存档' % year
            
        if posts.count() == 0:
            self.fof()
        else:
            self.dumpMultiPage(posts, drct, page_cursor, 'index.html')