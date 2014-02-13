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
from google.appengine.ext.db import Key
from google.appengine.api.datastore_errors import BadValueError
from google.appengine.api.urlfetch import DownloadError

from model import Comment, Post
from util.akismet import Akismet
from mako.lookup import TemplateLookup

from datetime import datetime, timedelta
import logging, urllib, Cookie, os, math

api = Akismet(agent='wokanblog')

class NewComment(webapp.RequestHandler):
    def post(self, slug):
        slug = unicode(urllib.unquote(slug), 'utf-8')
        k = Post.get_by_key_name('_' + slug).key()
        
        name, email, url, content, captcha = (self.request.get(key) for key in ['name', 'email', 'url', 'content', 'captcha'])
        
        try:
            if content.strip() == '':
                raise BadValueError('Content should not be empty')
            c = Comment()
            c.post = k
            c.authorName = name
            c.authorEmail = email
            c.url = url
            c.ip = self.request.remote_addr
            c.content = content.replace('\n', '<br/>')
            c.status = 'approved'

            if captcha != u'\u4e0d\u662f':
                logging.info(u'截获垃圾，发自：%s，内容：%s' % (name, content))
                c.status = 'spam'
                #c.put()    //20131201: dont't put
                #发邮件给我
                sender_address = 'pizzamx@gmail.com'
                user_address = "root+blog@wokanxing.info"
                subject = '[BLOG]Spam detected'
                msg = 'name: %s\nmail: %s\nurl: %s\ncontent: %s\n' % (name, email, url, content)
                mail.send_mail(sender_address, user_address, subject, msg)
                
                self.response.out.write('都说了写 ** 不是 ** 两个字了！')
                return
            """
            try:
                if api.key is None:
                    logging.error("No 'apikey.txt' file.")
                elif not api.verify_key():
                    logging.error("The API key is invalid.")
                else:
                    #会误杀twenty……无语
                    if name != 'twenty' and api.comment_check(content.encode('utf-8'), {'comment_author': name.encode('utf-8'), 'comment_author_email': email, 'comment_author_url': url}):
                        logging.info(u'截获垃圾，发自：%s，内容：%s' % (name, content))
                        c.status = 'spam'
                        c.put()
                        #发邮件给我
                        sender_address = 'pizzamx@gmail.com'
                        user_address = "root+blog@wokanxing.info"
                        subject = '[BLOG]Spam detected'
                        msg = 'name: %s\nmail: %s\nurl: %s\ncontent: %s\n' % (name, email, url, content)
                        mail.send_mail(sender_address, user_address, subject, msg)
                        
                        self.response.out.write('垃圾过滤系统错误分类了您的留言，替他向您说声对不起！请不要惊慌，保持冷静，拿起电话，联系pizza！或者不用理会也行，我会在收到系统报告之后第一时间复原您的评论，无需重发，谢谢！')
                        return
            except DownloadError:
                logging.error('Cannot reach akismet')
                
            """
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
        SIZE = 20
        comments = Comment.all()
        page = 1 if not page else int(page)
        pageCount = int(math.ceil(float(comments.count()) / SIZE))
        comments = comments.order('-date').fetch(SIZE, (page - 1) * SIZE)
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
        c = Comment.get_by_id(int(id))
        if c:
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
            
class MarkHam(webapp.RequestHandler):
    def post(self, id):
        c = Comment.get_by_id(int(id))
        if c:
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

            self.response.out.write('failed')