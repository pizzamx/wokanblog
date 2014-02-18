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

from google.appengine.api import users
from google.appengine.datastore.datastore_query import Cursor


from mako.template import Template
from mako.lookup import TemplateLookup

from model import Post, Comment, CST
from model import Image
from util import memcached

from datetime import tzinfo, timedelta, datetime, date
import os, logging, urllib, math, calendar, re

import util, widget, urllib

class QueryBase(webapp2.RequestHandler):
    def __init__(self, request=None, response=None):
        super(QueryBase, self).__init__(request=request, response=response)
        #页面标题
        self.title = ''
        
    def dumpMultiPage(self, posts, drct, page_cursor, tplName):
        #baseUrl代表根域名，redirectUrl用于（可能的）跳转
        url = self.request.url
        baseUrl = url[:url.find('/', 8)]    #8 for https
        
        #分页
        page_size = util.POST_PER_PAGE_FOR_HANDSET if self.isFromMobileDevice() else util.POST_PER_PAGE

        if drct == 'next':
            cursor = Cursor(urlsafe=page_cursor)
        """    
        elif drct == 'prev':
            cursor = Cursor(urlsafe=page_cursor).reversed()
            page_size += 1
        """
        else:   #没有传这个参数说明是首页（第一页）
            cursor = None
            
        posts, next_cursor, more = posts.order(-Post.date).fetch_page(page_size, start_cursor=cursor)
        
        if drct == 'next':
            next_page = next_cursor.urlsafe() if more else ''
            prev_page = cursor.urlsafe()
        """
        elif drct == 'prev':
            next_page = next_cursor.urlsafe()
            prev_page = cursor.urlsafe() if more else ''
            posts = posts[1:]
        """
        else:
            next_page = next_cursor.urlsafe() if more else ''
            prev_page = ''
        
        #分页按钮的链接前缀（最后要以/结束）
        if re.match(r'.*?/page/(prev|next)/\S*', url, re.IGNORECASE):
            path = re.sub(r'(.*?/)page/(prev|next)/\S*', r'\1', url)
        else:
            path = url if url.endswith('/') else url + '/'
        
        #主题
        cookies = self.request.cookies
        theme = cookies['theme'] if 'theme' in cookies else ''
        
        #分页
        """
        rg = []
        if pageCount <= 4:
            rg = range(pageCount, 0, -1)
        else:
            if page_cursor >= 3 and page_cursor <= pageCount - 2:
                rg = range(page_cursor + 2, page_cursor - 3, -1)
            elif page_cursor < 3:
                rg = range(page_cursor + 2, 0, -1)
            else:
                rg = range(pageCount, page_cursor - 3, -1)
        """
        
        #输出
        template = self.getTemplate(tplName)
        args = {
            'baseUrl': baseUrl, 
            'redirectUrl': url, 
            'posts': posts, 
            'isAdmin': users.is_current_user_admin(), 
            'calendar': widget.Calendar(path), 
            'widgets': [widget.SearchBox(), widget.BlogUpdates(), widget.RecentComment(), widget.TagCloud()], 
            'theme': theme,
            'next_page': next_page,
            'prev_page': prev_page,
            'pagePath': path, 
            'title': self.title
        }
        
        self.response.write(template.render_unicode(**args))
    
    def getTemplate(self, name):
        #读取模板文件
        mylookup = TemplateLookup(directories=[os.path.join(os.path.dirname(__file__), 'template')], 
                                  #module_directory=os.path.join(os.path.dirname(__file__), 'tpl_cache'),     #GAE不支持tempfile.mkstemp()
                                  format_exceptions=True)
        return mylookup.get_template(name)
        
    def isFromMobileDevice(self):
        ua = self.request.headers['User-Agent']
        return True if re.search(r'(iPhone|iPod|iPad|BlackBerry|Android)', ua) else False
    
    #知道啥意思不……four O four……lol
    def fof(self):
        cookies = self.request.cookies
        theme = cookies['theme'] if 'theme' in cookies else ''
        ua = self.request.headers['User-Agent']
        if self.isFromMobileDevice():
            template = self.getTemplate('404_m.html')
        else:
            template = self.getTemplate('404.html')
        self.response.set_status(404)
        logging.info('Invalid request: %s' % self.request.path)
        self.response.write(template.render_unicode(title = u'出错啦', theme=theme, uri=self.request.path))

class Index(QueryBase):
    def get(self, drct=None, page_cursor=None):
        allPosts = Post.query(Post.isPage == False)
        page = 'mindex.html' if self.isFromMobileDevice() else 'index.html'
        self.dumpMultiPage(allPosts, drct, page_cursor, page)

class Single(QueryBase):
    def get(self, y, m, slug):
        #sure not empty?
        slug = unicode(urllib.unquote(slug), 'utf-8')
        post = Post.get_by_id('_' + slug)
        cs = Comment.query(Comment.post == post.key).order(+Comment.date)
        if not post or post.isPrivate and not users.is_current_user_admin():
            self.fof()
        else:
            (pp, np) = self.getAdjTitles(post)
            url = self.request.url
            baseUrl = url[:url.find('/', 8)]    #8 for https
            rc = self.request.cookies
            cd = {}
            for k in ('c_name', 'c_email', 'c_url', 'c_captcha'):
                if k not in rc:
                    cd[k] = ''
                else:
                    cd[k] = urllib.unquote(str(rc[k])).decode('utf-8')
            theme = rc['theme'] if 'theme' in rc else ''
            if self.isFromMobileDevice():
                template = self.getTemplate('msingle.html')
            else:
                template = self.getTemplate('single.html')
            self.response.write(template.render_unicode(baseUrl=baseUrl, isAdmin=users.is_current_user_admin(), post=post, cs=cs, pp=pp, np=np, cookies=cd, theme=theme, single=True))
    
    def getAdjTitles(self, p):
        found = False
        nk = pk = None
        date_of_post = p.date
        posts = Post.query()
        if not users.is_current_user_admin():
            posts = posts.filter(Post.isPrivate == False)
        np = posts.order(-Post.date).filter(Post.date < date_of_post).get()
        pp = posts.order(+Post.date).filter(Post.date > date_of_post).get()
        return (pp, np)
            
class Page(QueryBase):
    def get(self, slug):
        post = Post.get_by_id('_' + slug)
        if not post:
            self.fof()
        else:
            cs = Comment.query(Comment.post == post.key).order(+Comment.date)
            url = self.request.url
            baseUrl = url[:url.find('/', 8)]    #8 for https
            cookies = self.request.cookies
            for k in ('c_name', 'c_email', 'c_url', 'c_captcha'):
                if k not in cookies:
                    cookies[k] = ''
            theme = cookies['theme'] if 'theme' in cookies else ''
            if self.isFromMobileDevice():
                template = self.getTemplate('msingle.html')
            else:
                template = self.getTemplate('single.html')
            self.response.write(template.render_unicode(baseUrl=baseUrl, isAdmin=users.is_current_user_admin(), cs=cs, post=post, redirectUrl=url, cookies=cookies, theme=theme, page=True))
            
class ServeImage(webapp2.RequestHandler):
    def get(self, name):
        hkeys = self.request.headers.keys()
        if 'Referer' in hkeys: 
            referer = self.request.headers['Referer']
            if referer:
                if re.search(r'https?:\/\/.*?\.wokanxing\.info.*', referer, re.I) or referer.find('appspot.com') != -1:
                    img = Image.get_by_id('_' + name)
                    if img:
                        self.response.headers['Content-Type'] = 'image/%s' % name[name.rfind('.') + 1:]
                        self.response.write(img.data)
                else:
                    logging.warning('Disallowed referer: ' + referer)
        
class Feed(QueryBase):
    def get(self, dumpComments):
        data, updateTime = self.query(dumpComments)
        url = self.request.url
        baseUrl = url[:url.find('/', 8)]    #8 for https
        template = self.getTemplate('comment_atom.xml' if dumpComments else 'atom.xml')
        self.response.headers['Content-type'] = 'application/xml; charset=utf-8'
        #TODO: X-Pingback
        self.response.write(template.render_unicode(baseUrl=baseUrl, data=data, now=updateTime))
        
    def query(self, dumpComments):
        return self.queryCommentFeed() if dumpComments else self.queryPostFeed() 

    @memcached(-1)
    def queryPostFeed(self):
        now = datetime.now().replace(tzinfo=CST()).isoformat()
        return Post.query(Post.isPage == False, Post.isPrivate == False).order(-Post.date).fetch(10), now

    @memcached(-1)
    def queryCommentFeed(self):
        now = datetime.now().replace(tzinfo=CST()).isoformat()
        return Comment.query(Comment.status == 'approved').order(+Comment.date).fetch(10), now