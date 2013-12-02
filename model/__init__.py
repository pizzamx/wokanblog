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

from google.appengine.ext import db
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
        
class UrlProperty(db.Property):
    def validate(self, value):
        if value and value.strip() != '':
            if not value.lower().startswith('http://'):
                value = 'http://' + value
            scheme, domain, path, params, query, fragment = urlparse.urlparse(value)
            if not domain:
                raise BadValueError('Invalid URL: %s' % value)
        return value

    data_type = unicode
    
class EmailProperty(db.Property):
    #自带的那个居然不验证....
    def validate(self, value):
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

class Post(db.Model):
    #author = db.UserProperty()
    title = db.StringProperty()
    slug = db.StringProperty()
    content = db.TextProperty()
    tags = db.ListProperty(db.Key)
    date = db.DateTimeProperty(auto_now_add=True)
    wpId = db.IntegerProperty()
    isPage = db.BooleanProperty(default=False)
    isPrivate = db.BooleanProperty(default=False)
    
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
            tag = Tag.get(tagKey)
            tagLinks.append('<a href="/tag/%s">%s</a>' % (tag.name, tag.name))
        return string.join(tagLinks, ', ')
    
    def getTagStr(self):
        return string.join(((Tag.get(k)).name for k in self.tags), ', ')

    def makeLink(self):
        if self.isPage:
            return '/%s' % self.slug
        return '/%d/%s/%s' % (self.date.year, str(self.date.month).rjust(2, '0'), self.slug)
    
    def getEditLink(self):
        if self.isPage:
            return '/%s/edit' % self.slug
        return '/%d/%s/%s/edit' % (self.date.year, str(self.date.month).rjust(2, '0'), self.slug)
        
    def getCommentCount(self):
        n = 0
        for c in self.comment_set:
            if c.status == 'approved':
                n += 1
        return n

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
    
class Comment(db.Model):
    authorEmail = EmailProperty()
    authorName = db.StringProperty()
    #url should be empty-allowed so no LinkProperty...maybe Expando?
    url = UrlProperty()
    post = db.ReferenceProperty(Post)
    content = db.TextProperty()
    ip = db.StringProperty()
    isTrackback = db.BooleanProperty()
    date = db.DateTimeProperty(auto_now_add=True)
    status = db.StringProperty()    #'approved' or 'spam'
    
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
        return '%s#c_%s' % (self.post.makeLink(), self.key().id())

    @filter_html
    def strippedContent(self):
        #return self.content
        return re.sub(r'(?ms)\[quote.*?\](.*?)\[/quote\]', r'<blockquote>\1</blockquote>', self.content)
            
class Tag(db.Model):
    name = db.StringProperty()
    
class Image(db.Model):
    src = db.StringProperty()
    name= db.StringProperty()
    data = db.BlobProperty()
    
    def fetch(self):
        try:
            stream = urllib2.urlopen(self.src)
            self.data = db.Blob(stream.read())
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
        
class Blogroll(db.Model):
    name = db.StringProperty()
    desc = db.StringProperty(required=False, default='')
    blogUrl = UrlProperty()
    feedUrl = UrlProperty()
    lastUpdate = db.DateTimeProperty(default=datetime(2005, 1, 1))
    lastTitle = db.StringProperty(default='')

    def getCSTDate(self):
        return self.date.replace(tzinfo=UTC()).astimezone(CST())
        #return self.lastUpdate.replace(tzinfo=CST())

class SharedCounter(db.Model):
    name = db.StringProperty()
    count = db.IntegerProperty(required=True, default=0)