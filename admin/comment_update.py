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

from google.appengine.api import urlfetch, memcache, mail
from google.appengine.ext import webapp
from google.appengine.ext import ndb
from google.appengine.ext.db import Key
from google.appengine.api.datastore_errors import BadValueError
from google.appengine.api.urlfetch import DownloadError

from model import Comment, Post
#from util.akismet import Akismet
from mako.lookup import TemplateLookup

from datetime import datetime, timedelta
import logging, urllib, urllib2, Cookie, os, math, json

#api = Akismet(agent='wokanblog')

class NewComment(webapp.RequestHandler):
    def post(self, slug):
        slug = unicode(urllib.unquote(slug), 'utf-8')
        k = Post.get_by_id('_' + slug).key
        
        name, email, url, content, captcha = (self.request.get(key) for key in ['name', 'email', 'url', 'content', 'g-recaptcha-response'])
        
        try:
            if content.strip() == '':
                raise BadValueError('Content should not be empty')
            c = Comment(parent=k)
            #c.post = k
            c.authorName = name
            c.authorEmail = email
            c.url = url
            c.ip = self.request.remote_addr
            c.content = content.replace('\n', '<br/>')
            c.status = 'approved'

            """
            if captcha != 'zheteng':
                logging.info(u'截获垃圾，发自：%s，内容：%s' % (name, content))
                c.status = 'spam'
                #c.put()    //20131201: dont't put
                #发邮件给我
                sender_address = 'pizzamx@gmail.com'
                user_address = "root+blog@wokanxing.info"
                subject = '[BLOG]Spam detected'
                msg = 'name: %s\nmail: %s\nurl: %s\ncontent: %s\n' % (name, email, url, content)
                mail.send_mail(sender_address, user_address, subject, msg)
                
                self.response.out.write('请输入「折腾」的拼音，小写，中间不带空格')
                return
            """
            
            try:
                payload = {
                    'secret': '6Ld_PCATAAAAAN9oE8SGh3swJKjlNx0pAxSHXO5d',
                    'response': captcha,
                    'remoteip': c.ip
                }
                req = urllib2.Request('https://www.google.com/recaptcha/api/siteverify', urllib.urlencode(payload))
                resp = urllib2.urlopen(req).read()
                resp = json.loads(resp)
                if not (resp.has_key('success') and resp['success'] == True):
                    if resp.has_key('error-codes'):
                        self.response.out.write('reCaptcha 验证失败，原因：' + resp['error-codes'])
                        return
                    else:
                        raise Exception(resp)
            except Exception, e:
                logging.fatal("Exception while analyzing reCaptcha: %s" % e.reason)
                self.response.out.write('reCaptcha 验证失败，不知道为啥……')
                return
            c.put()
            
            for k, v in {'c_name': name, 'c_email': email, 'c_url': url, 'c_captcha': captcha}.iteritems():
                cookie = Cookie.BaseCookie()
                cookie[k] = urllib.quote(v.encode('utf-8'))
                cookie[k]['path'] = '/'
                cookie[k]['expires'] = (datetime.now() + timedelta(days=999)).strftime('%a, %d-%a-%Y %H:%M:%S')
                self.response.headers['Set-Cookie'] = cookie.output(header='')
            
            memcache.delete('getLatestComments')
            memcache.delete('queryCommentFeed')
            
            self.redirect(c.makeLink())
        except BadValueError:
            self.response.out.write('请输入大名及留言，如果留下了邮件地址或链接，请保证格式正确:-)')
        
class ListComments(webapp.RequestHandler):
    def get(self, page):
        SIZE = 30
        comments = Comment.query()
        page = 1 if not page else int(page)
        pageCount = int(math.ceil(float(comments.count()) / SIZE))
        comments = comments.order(-Comment.date).fetch(SIZE, offset=(page - 1) * SIZE)
        mylookup = TemplateLookup(directories=[os.path.join(os.path.dirname(__file__), 'template')])
        template = mylookup.get_template('manage_comments.html')
        #分页
        rg = []
        if pageCount <= 4:
            rg = range(pageCount, 0, -1)
        else:
            if page >= 3 and page <= pageCount - 2:
                rg = range(page + 2, page - 3, -1)
            elif page < 3:
                rg = range(page + 2, 0, -1)
            else:
                rg = range(pageCount, page - 3, -1)
        #如果缩放过，返回缩略图的路径，让客户端反推原图的路径
        self.response.out.write(template.render_unicode(comments=comments, pageCount=pageCount, currentPage=page, rg=rg, pagePath='/admin/comments/'))

class ReportSpam(webapp.RequestHandler):
    def post(self, id):
        c_key = ndb.Key(urlsafe=id)
        c = c_key.get()
        if c:
            """
            try:
                if api.key is None:
                    logging.error("No 'apikey.txt' file.")
                elif not api.verify_key():
                    logging.error("The API key is invalid.")
                else:
                    api.submit_spam(c.content.encode('utf-8'), {'comment_author': c.authorName.encode('utf-8'), 'comment_author_email': c.authorEmail, 'comment_author_url': c.url})
                    c.status = 'spam'
                    c.put()
                    memcache.delete('getLatestComments')
                    self.response.out.write('ok')
                    return
            except DownloadError:
                logging.error('Cannot reach akismet')

            self.response.out.write('failed')
            """
            c.status = 'spam'
            c.put()
            memcache.delete('getLatestComments')
            self.response.out.write('ok')
            return
        else:
            self.response.out.write('Comment %s not found' % id)
            
class MarkHam(webapp.RequestHandler):
    def post(self, id):
        c_key = ndb.Key(urlsafe=id)
        c = c_key.get()
        if c:
            """
            try:
                if api.key is None:
                    logging.error("No 'apikey.txt' file.")
                elif not api.verify_key():
                    logging.error("The API key is invalid.")
                else:
                    api.submit_ham(c.content.encode('utf-8'), {'comment_author': c.authorName.encode('utf-8'), 'comment_author_email': c.authorEmail, 'comment_author_url': c.url})
                    c.status = 'approved'
                    c.put()
                    memcache.delete('getLatestComments')
                    self.response.out.write('ok')
                    return
            except DownloadError:
                logging.error('Cannot reach akismet')
            """
            c.status = 'approved'
            c.put()
            memcache.delete('getLatestComments')
            self.response.out.write('ok')
            return
        else:
            self.response.out.write('Comment %s not found' % id)
            