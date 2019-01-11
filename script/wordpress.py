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

import string, urlparse, logging, urllib, re
from xml.dom import minidom
from datetime import datetime

from google.appengine.ext import db, webapp
from google.appengine.api.datastore_errors import BadValueError
from google.appengine.api import memcache

from model import Post, Comment, Tag
from model import Image
from util import trackback

wpns = 'http://wordpress.org/export/1.0/'
cns = 'http://purl.org/rss/1.0/modules/content/'
FILENAME = 'wordpress.xml'

def clearDatastore():
    db.delete(Post.all())
    db.delete(Comment.all().fetch(500))
    db.delete(Comment.all().fetch(500))
    db.delete(Tag.all())
    memcache.flush_all()

def getText(parent, tagName, ns=None):
    if ns:
        e = parent.getElementsByTagNameNS(ns, tagName)[0]
    else:
        e = parent.getElementsByTagName(tagName)[0]

    if e.firstChild:
        return e.firstChild.data
    else:
        return None

def putImgs(content):
    srcs = re.findall(r'(?i)<a.*?href="(http://[^"]*?(?:png|jpg|jpeg|gif))".*?>', content) + re.findall(r'(?i)<img.*?src="(http://.*?)"', content)
    for src in srcs:
        name = src[src.rfind('/') + 1:]
        img = Image(src=src, name=name, id='_' + name)
        img.fetch()
        content = content.replace(src, '/img/%s' % name)
        #content = re.sub(r'(?:<a .*?>)?(<img.*?src=")%s(".*?>)(?:</a>)?' % src, r'\1/img/%s\2' % name, content, re.IGNORECASE)
    return content

def mockPutImgs(content, out):
    srcs = re.findall(r'(?i)<a.*?href="(http://[^"]*?(?:png|jpg|jpeg|gif))".*?>', content)
    for src in srcs:
        name = src[src.rfind('/') + 1:]
        content = content.replace(src, '/img/%s' % name)
        print>>out, src, '\n'
        
    print>>out, '<link __________ img>\n'

    srcs = re.findall(r'(?i)<img.*?src="(http://.*?)"', content)
    for src in srcs:
        name = src[src.rfind('/') + 1:]
        content = content.replace(src, '/img/%s' % name)
        print>>out, src, '\n'

    print>>out, '___________________________________________________\n'

def putPost(item):
    title = getText(item, 'title')
    slug = getText(item, 'post_name', wpns)
    slug = unicode(urllib.unquote(str(slug)), 'utf-8')
    type = getText(item, 'post_type', wpns)
    content = putImgs(getText(item, 'encoded', cns))
        
    try:
        date = datetime.strptime(getText(item, 'post_date_gmt', wpns), '%Y-%m-%d %H:%M:%S')     #page may not contain valid pub date
    except ValueError:
        date = datetime.now()
    post = Post(title=title, slug=slug, content=content, date=date, isPage=(type=='page'), id='_' + slug)
    post.put()
    return post

def associateTags(item, post):
    tags = []
    cs = item.getElementsByTagName('category')
    for c in cs:
        if c.hasAttribute('domain') and not c.hasAttribute('nicename') and c.getAttribute('domain') == 'tag':
            tagName = c.firstChild.data
            tag = Tag.get_by_id('_' + tagName)
            post.tags.append(tag.key())
    if len(cs):
        post.put()

def putComments(item, post):
    cts = item.getElementsByTagNameNS(wpns, 'comment')
    comments = []
    for ct in cts:
        approve_status = getText(ct, 'comment_approved', wpns)
        if approve_status != 'spam':
            authorEmail = getText(ct, 'comment_author_email', wpns)
            #authorEmail, authorName, url, content, ip, date
            authorEmail = getText(ct, 'comment_author_email', wpns)
            authorName = getText(ct, 'comment_author', wpns)
            url = getText(ct, 'comment_author_url', wpns)
            if url and url.strip() != '':
                scheme, domain, path, params, query, fragment = urlparse.urlparse(url)
                if (not scheme or (scheme != 'file' and not domain) or (scheme == 'file' and not path)):
                    url = ''
            content = getText(ct, 'comment_content', wpns)
            ip = getText(ct, 'comment_author_IP', wpns)
            isTrackback = getText(ct, 'comment_type', wpns) == 'pingback'
            date = datetime.strptime(getText(ct, 'comment_date_gmt', wpns), '%Y-%m-%d %H:%M:%S')
    
            try:
                c = Comment(post=post.key(), authorName=authorName, authorEmail=authorEmail, url=url, ip=ip, content=content, date=date, isTrackback=isTrackback)
            except BadValueError:
                logging.error('Bad email: %s' % authorEmail)
                c = Comment(post=post.key(), authorName=authorName, authorEmail='', url=url, ip=ip, content=content, date=date, isTrackback=isTrackback)
            comments.append(c)
    if len(comments):
        db.put(comments)
        
class Count(webapp.RequestHandler):
    def get(self):
        clearDatastore()
        self.putAllTags()

        items = self.doc.getElementsByTagName('item')
        i = 0
        result = []
        for item in items:
            title = getText(item, 'title')
            status = getText(item, 'status', wpns)
            if status == 'publish' and getText(item, 'post_type', wpns) in ['post', 'page']:
                result.append(str(i))
            i += 1
        self.response.headers['content-type'] = 'text/plain'
        self.response.out.write(string.join(result, ','))
    
    def putAllTags(self):
        self.doc = minidom.parse(FILENAME)
        tagEs = self.doc.getElementsByTagNameNS(wpns, 'tag')
        tags = []
        for tagE in tagEs:
            tagName = getText(tagE, 'tag_name', wpns)
            tag = Tag(name=tagName, id='_' + tagName)
            tags.append(tag)
        if len(tags):
            db.put(tags)
            
class Process(webapp.RequestHandler):
    def get(self, index):
        doc = minidom.parse(FILENAME)
        items = doc.getElementsByTagName('item')
        item = items[int(index)]
        
        status = getText(item, 'status', wpns)
        if status == 'publish' and getText(item, 'post_type', wpns) in ('post', 'page'):
            post = putPost(item)
            associateTags(item, post)
            putComments(item, post)
            
class TestWPImport(webapp.RequestHandler):
    def setUp(self):
        self.doc = minidom.parse(FILENAME)
        self.items = self.doc.getElementsByTagName('item')

    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.setUp()
        for item in self.items:
            status = getText(item, 'status', wpns)
            if status == 'publish' and getText(item, 'post_type', wpns) in ('post', 'page'):
                content = getText(item, 'encoded', cns)
                mockPutImgs(content, self.response.out)
