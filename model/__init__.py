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

from google.appengine.ext import ndb
from google.appengine.api.datastore_errors import BadValueError

from datetime import tzinfo, timedelta, datetime
from util import filter_html

import hashlib, urlparse, string, urllib2, logging, re, string

class UTC(tzinfo):
    def utcoffset(self, dt):
        return timedelta(seconds=0)

class CST(tzinfo):
    def utcoffset(self, dt):
        return timedelta(hours=8)
    def dst(self, dt):
        return timedelta(0)
        
class UrlProperty(ndb.StringProperty):
    def _validate(self, value):
        if value and value.strip() != '':
            if not value.lower().startswith(('http://', 'https://')):
                value = 'http://' + value
            scheme, domain, path, params, query, fragment = urlparse.urlparse(value)
            if not domain:
                raise BadValueError('Invalid URL: %s' % value)
        return value

    data_type = unicode
    
class EmailProperty(ndb.StringProperty):
    #自带的那个居然不验证....
    def _validate(self, value):
        #@see is_email in formatting.php, wordpress
        if value and value.strip() != '':
            if len(value) < 6:
                raise BadValueError('Email too short: %s' % value)
            reg = r'^([a-z0-9+_]|\-|\.)+@(([a-z0-9_]|\-)+\.)+[a-z]{2,6}$'
            if value.find('@') != -1 and value.find('.') != -1 and re.match(reg, value, re.IGNORECASE):
                return value
            raise BadValueError('Email validation failed: %s' % value)
            
        return value

    data_type = unicode

class Post(ndb.Model):
    #author = ndb.UserProperty()
    title = ndb.StringProperty()
    slug = ndb.StringProperty()
    content = ndb.TextProperty()
    tags = ndb.KeyProperty(repeated=True)
    date = ndb.DateTimeProperty(auto_now_add=True)
    wpId = ndb.IntegerProperty()
    isPage = ndb.BooleanProperty(default=False)
    isPrivate = ndb.BooleanProperty(default=False)
    
    def getCSTDate(self):
        #难道dev server自动添加的时间带本地时区？这和文档冲突啊
        #return self.date.replace(tzinfo=CST())
        return self.date.replace(tzinfo=UTC()).astimezone(CST())
        
    def getMonthDisplay(self):
        m = self.date.replace(tzinfo=CST()).month
        #太砢碜了.........
        return ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')[m - 1]
        
    def getTagLinks(self):
        tagLinks = []
        for tagKey in self.tags:
            tag = tagKey.get()
            tagLinks.append('<a href="/tag/%s">%s</a>' % (tag.name, tag.name))
        return string.join(tagLinks, ', ')
    
    def getTagStr(self):
        return string.join(((k.get()).name for k in self.tags), ', ')

    def makeLink(self):
        if self.isPage:
            return '/%s' % self.slug
        return '/%d/%s/%s' % (self.date.year, str(self.date.month).rjust(2, '0'), self.slug)
    
    def getEditLink(self):
        if self.isPage:
            return '/%s/edit' % self.slug
        return '/%d/%s/%s/edit' % (self.date.year, str(self.date.month).rjust(2, '0'), self.slug)
        
    def getCommentCount(self):
        #FIXME: 这个数字不准……因为以前的评论不是 ndb 创建的……如果要重建一遍的话记得考虑引用关系（复杂……
        return Comment.query(ancestor=self.key).count()
        """
        n = 0
        for c in Comment.query(ancestor=self.key).fetch(projection=Comment.status):
            if c.status == 'approved':
                n += 1
        return n
        """

    @filter_html
    def strippedContent(self):
        return self.content

    @filter_html
    def briefContent(self):
        t = self.content.split('<!--more-->')
        if len(t) > 1:
            return t[0] + u'<p><a href="%s">继续阅读</a></p>' % self.makeLink()
        else:
            return t[0]
    
class Comment(ndb.Model):
    authorEmail = EmailProperty()
    authorName = ndb.StringProperty()
    #url should be empty-allowed so no LinkProperty...maybe Expando?
    url = UrlProperty()
    post = ndb.KeyProperty(kind=Post)
    content = ndb.TextProperty()
    ip = ndb.StringProperty()
    isTrackback = ndb.BooleanProperty(default=False)
    date = ndb.DateTimeProperty(auto_now_add=True)
    status = ndb.StringProperty()    #'approved' or 'spam'
    
    def getCSTDate(self):
        #return self.date.replace(tzinfo=CST())
        return self.date.replace(tzinfo=UTC()).astimezone(CST())
    
    def getGravatar(self):
        return 'http://www.gravatar.com/avatar/%s?s=48&r=x&d=retro' % hashlib.md5(self.authorEmail.lower()).hexdigest()
    
    def getAuthorLink(self):
        if self.url:
            return '<a href="%s">%s</a>' % (self.url, self.authorName)
        else:
            return self.authorName
        
    def makeLink(self):
        return '%s#c_%s' % (self.key.parent().get().makeLink(), self.key.id())

    @filter_html
    def strippedContent(self):
        #return self.content
        return re.sub(r'(?ms)\[quote.*?\](.*?)\[/quote\]', r'<blockquote>\1</blockquote>', self.content)
            
class Tag(ndb.Model):
    name = ndb.StringProperty()
    
class Image(ndb.Model):
    src = ndb.StringProperty()
    name= ndb.StringProperty()
    data = ndb.BlobProperty()
    
    def fetch(self):
        try:
            stream = urllib2.urlopen(self.src)
            self.data = ndb.Blob(stream.read())
            stream.close()
            self.put()
            return True
        except:
            logging.error('Image fetch failed: ' + self.src)
            return False
    
    @property
    def width(self):
        pass
        
    @property
    def height(self):
        pass
        
class Blogroll(ndb.Model):
    name = ndb.StringProperty()
    desc = ndb.StringProperty(required=False, default='')
    blogUrl = UrlProperty()
    feedUrl = UrlProperty()
    lastUpdate = ndb.DateTimeProperty(default=datetime(2005, 1, 1))
    lastTitle = ndb.StringProperty(default='')

    def getCSTDate(self):
        return self.date.replace(tzinfo=UTC()).astimezone(CST())
        #return self.lastUpdate.replace(tzinfo=CST())

class SharedCounter(ndb.Model):
    name = ndb.StringProperty()
    count = ndb.IntegerProperty(required=True, default=0)