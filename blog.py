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

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

from flask import (Blueprint, abort, redirect, render_template, request,
                   response)
from flask.helpers import make_response, url_for
from google.appengine.api import memcache, users
from google.appengine.api.datastore_errors import BadValueError
from google.appengine.datastore.datastore_query import Cursor

import util
import widget
from model import CST, Comment, Image, Post, Tag
from util import login_required, memcached

bp = Blueprint('admin', __name__)


# 输出页面之前的检查。目前只有一个功能：为创建和谐社会判断 IP 地址来源
def render_tpl(page, **args):
    # FIXME: Feed output routine should be another branch
    is_civil, ccode = util.is_from_civilization(request)
    if not is_civil:
        if util.is_mobile_dev(request):
            page = 'mChina.html'
        else:
            page = 'China.html'
    return render_template(page, **args)

# 知道啥意思不……four O four……lol


@bp.errorhandler(404)
def fof():
    cookies = request.cookies
    theme = cookies['theme'] if 'theme' in cookies else ''
    if util.is_mobile_dev(request):
        page = '404_m.html'
    else:
        page = '404.html'
    logging.info('Invalid request: %s' % request.path)
    return render_template(page, theme=theme, uri=request.path, title='出错啦！'), 404


@bp.route('/')
@bp.route('/page/<direction>/<page_cursor>')
def show_home(direction, page_cursor):
    all_posts = Post.query(Post.isPage == False)
    # 分页
    page_size = util.POST_PER_PAGE_FOR_HANDSET if util.is_mobile_dev(
        request) else util.POST_PER_PAGE

    if direction == 'next':
        cursor = Cursor(urlsafe=page_cursor)
    else:
        # 没有传这个参数说明是首页（第一页）
        cursor = None

    posts, next_cursor, more = all_posts.order(-Post.date).fetch_page(page_size,
                                                                      start_cursor=cursor)

    if direction == 'next':
        next_page = next_cursor.urlsafe() if more else ''
        prev_page = cursor.urlsafe()
    # elif drct == 'prev':
    #    next_page = next_cursor.urlsafe()
    #    prev_page = cursor.urlsafe() if more else ''
    #    posts = posts[1:]
    else:
        next_page = next_cursor.urlsafe() if more else ''
        prev_page = ''

    # 分页按钮的链接前缀（最后要以/结束）
    url = request.url
    base_url = url[:url.find('/', 8)]  # 8 for https
    if re.match(r'.*?/page/(prev|next)/\S*', url, re.IGNORECASE):
        path = re.sub(r'(.*?/)page/(prev|next)/\S*', r'\1', url)
    else:
        path = url if url.endswith('/') else url + '/'

    # 主题
    cookies = request.cookies
    theme = cookies['theme'] if 'theme' in cookies else ''

    # 请求来源
    _r, ccode = util.is_from_civilization(request)
    args = {
        'baseUrl': base_url,
        'redirectUrl': url,
        'posts': posts,
        'isAdmin': users.is_current_user_admin(),
        'calendar': widget.Calendar(path),
        'widgets': [],
        'theme': theme,
        'next_page': next_page,
        'prev_page': prev_page,
        'pagePath': path,
        'ccode': ccode
    }

    page = 'mindex.html' if util.is_mobile_dev(request) else 'index.html'
    return render_tpl(page, **args)


@bp.route('/<int:y>/<int:m>/<slug>')
def show_single_post(y, m, slug):
    # sure not empty?
    slug = str(urllib.parse.unquote(slug), 'utf-8')
    post = Post.get_by_id('_' + slug)
    cs = Comment.query(ancestor=post.key).filter(
        Comment.status == 'approved').order(+Comment.date)
    if not post or post.isPrivate and not users.is_current_user_admin():
        abort(404)
    else:
        (pp, np) = get_adj_titles(post)
        url = request.url
        base_url = url[:url.find('/', 8)]  # 8 for https
        rc = request.cookies
        cd = {}
        for k in ('c_name', 'c_email', 'c_url', 'c_captcha'):
            if k not in rc:
                cd[k] = ''
            else:
                cd[k] = urllib.parse.unquote(str(rc[k])).decode('utf-8')
        theme = rc['theme'] if 'theme' in rc else ''
        if util.is_mobile_dev(request):
            page = 'msingle.html'
        else:
            page = 'single.html'
        # 请求来源
        _r, ccode = util.is_from_civilization(request)
        args = {
            'baseUrl': base_url, 'isAdmin': users.is_current_user_admin(),
            'post': post, 'cs': cs, 'pp': pp, 'np': np, 'cookies': cd, 'theme': theme,
            'single': True, 'ccode': ccode}
        return render_tpl(page, **args)


def get_adj_titles(p):
    found = False
    nk = pk = None
    date_of_post = p.date
    posts = Post.query()
    if not users.is_current_user_admin():
        posts = posts.filter(Post.isPrivate == False)
    np = posts.order(-Post.date).filter(Post.date < date_of_post).get()
    pp = posts.order(+Post.date).filter(Post.date > date_of_post).get()
    return (pp, np)


@bp.route('/<page_slug>')
def show_page(page_slug):
    post = Post.get_by_id('_' + page_slug)
    if not post:
        abort(404)
    else:
        cs = Comment.query(ancestor=post.key).filter(
            Comment.status == 'approved').order(+Comment.date)
        url = request.url
        base_url = url[:url.find('/', 8)]  # 8 for https
        cookies = request.cookies
        for k in ('c_name', 'c_email', 'c_url', 'c_captcha'):
            if k not in cookies:
                cookies[k] = ''
        theme = cookies['theme'] if 'theme' in cookies else ''
        if util.is_mobile_dev(request):
            page = 'msingle.html'
        else:
            page = 'single.html'
        # 请求来源
        _r, ccode = util.is_from_civilization(request)
        args = {'baseUrl': base_url, 'isAdmin': users.is_current_user_admin(),
                'cs': cs, 'post': post, 'redirectUrl': url, 'cookies': cookies,
                'theme': theme, 'page': True, 'ccode': ccode}
        return render_tpl(page, **args)


@bp.route('/<int:y>/<int:m>/<slug>/edit/')
@bp.route('/<slug>/edit/')
@login_required
def edit_post(y, m, slug):
    slug = str(urllib.parse.unquote(slug), 'utf-8')
    post = Post.get_by_id('_' + slug)

    tags = Tag.query()
    # 请求来源
    _r, ccode = util.is_from_civilization(request)
    args = {'tags': tags, 'post': post, 'ccode': ccode}
    return url_for('admin.new_post', **args)


@bp.route('/comment/<slug>', methods=['POST'])
def add_comment(self, slug):
    slug = str(urllib.parse.unquote(slug), 'utf-8')
    k = Post.get_by_id('_' + slug).key

    name, email, url, content, captcha = (
        request.form[key]
        for key in ['name', 'email', 'url', 'content', 'g-recaptcha-response'])

    try:
        if content.strip() == '':
            raise BadValueError('Content should not be empty')
        c = Comment(parent=k)
        # c.post = k
        c.authorName = name
        c.authorEmail = email
        c.url = url
        c.ip = request.remote_addr
        c.content = content.replace('\n', '<br/>')
        c.status = 'approved'

        try:
            payload = {
                'secret': '6Ld_PCATAAAAAN9oE8SGh3swJKjlNx0pAxSHXO5d',
                'response': captcha,
                'remoteip': c.ip
            }
            req = urllib.request.Request(
                'https://www.google.com/recaptcha/api/siteverify', urllib.parse.urlencode(payload))
            resp = urllib.request.urlopen(req).read()
            resp = json.loads(resp)
            if not ('success' in resp and resp['success'] == True):
                if 'error-codes' in resp:
                    response.out.write('reCaptcha 验证失败，原因：' + resp['error-codes'])
                    return
                else:
                    raise Exception(resp)
        except Exception as e:
            logging.fatal("Exception while analyzing reCaptcha: %s" % e.reason)
            response.out.write('reCaptcha 验证失败，不知道为啥……')
            return
        c.put()

        resp = make_response(redirect(c.makeLink()))
        for k, v in {
                'c_name': name, 'c_email': email, 'c_url': url, 'c_captcha': captcha}.items():
            resp.set_cookie(
                k, urllib.parse.quote(v.encode('utf-8')),
                expires=(datetime.now() + timedelta(days=999)).strftime('%a, %d-%a-%Y %H:%M:%S'))

        memcache.delete('getLatestComments')
        memcache.delete('queryCommentFeed')
        return resp
    except BadValueError:
        response.out.write('请输入大名及留言，如果留下了邮件地址或链接，请保证格式正确:-)')


@bp.route('/img/<img_name>')
def get_img(img_name):
    if 'Referer' in request.headers:
        referer = request.headers['Referer']
        if referer:
            if re.search(
                    r'https?:\/\/.*?\.wokanxing\.info.*', referer, re.I) or referer.find(
                    'appspot.com') != -1:
                img = Image.get_by_id('_' + img_name)
                if img:
                    resp = make_response(img.data)
                    resp.headers.set('Content-Type', 'image/%s' % img_name[img_name.rfind(
                        '.') + 1:])
                    # resp.headers.set('Content-Disposition', 'attachment', filename='%s' % img_name)
                    return resp
            else:
                logging.warning('Disallowed referer: ' + referer)


@bp.route('/feed/')
@memcached(-1)
def get_post_feed():
    now = datetime.now().replace(tzinfo=CST()).isoformat()
    url = request.url
    base_url = url[:url.find('/', 8)]
    posts = []
    is_civil, ccode = util.is_from_civilization(request)
    if is_civil:
        posts = Post.query(Post.isPage == False, Post.isPrivate ==
                           False).order(-Post.date).fetch(10)
    resp = make_response(render_template(
        'atom.xml', baseUrl=base_url, data=posts, now=now))
    resp.headers.set('Content-type', 'application/xml; charset=utf-8')
    return resp


@bp.route('/comments/feed/')
@memcached(-1)
def get_comment_feed():
    now = datetime.now().replace(tzinfo=CST()).isoformat()
    url = request.url
    base_url = url[:url.find('/', 8)]
    comments = []
    is_civil, ccode = util.is_from_civilization(request)
    if is_civil:
        comments = Comment.query(Comment.status == 'approved').order(-Comment.date).fetch(10)
    resp = make_response(render_template(
        'atom.xml', baseUrl=base_url, data=comments, now=now))
    resp.headers.set('Content-type', 'application/xml; charset=utf-8')
    return resp


"""
@bp.route('/<int:y>/<int:m>/<slug>/trackback/', methods=['POST'])
def handle_trackback(y, m, slug):
    logging.debug(request.body)
    post = Post.get_by_id('_' + slug)
    response.headers.add_header('Content-type', 'text/xml')

    tb = Comment()
    tb.isTrackback = True
    tb.post = post.key
    tb.title = urllib.parse.unquote(request.get('title'))
    tb.content = urllib.parse.unquote(request.get('excerpt'))
    try:
        tb.url = urllib.parse.unquote(request.get('url'))
    except BadValueError:
        self.response.out.write('''
                <?xml version="1.0" encoding="utf-8"?>
                <response>
                    <error>1</error>
                    <message>Malformed URL</message>
                </response>
            ''')
        return
    tb.authorName = urllib.parse.unquote(self.request.get('blog_name'))
    tb.authorEmail = 'test@example.com'  # TODO: better one?
    tb.ip = self.request.remote_addr
    # 5/25/14: 暂时停止接收！
    # tb.put()

    self.response.out.write('''
            <?xml version="1.0" encoding="utf-8"?>
            <response>
                <error>0</error>
            </response>
        ''')
"""
