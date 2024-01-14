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
import logging
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from xmlrpc.client import Error, ServerProxy

from flask import Blueprint, redirect, request
from flask.helpers import make_response, url_for
from flask.templating import render_template
from google.appengine.api import images,  memcache
from google.appengine.ext import db, ndb

import util
from model import Comment, Image, Post, Tag
from util import login_required

bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/write/', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'GET':
        tags = Tag.query()
        # 请求来源
        _r, ccode = util.is_from_civilization(request)
        return render_template('post_new.html', tags=tags, ccode=ccode)
    else:  # POST
        slug = request.form['slug']
        from_edit = request.form['edit'] == 'true'

        # TODO: 因为用slug做了key，所以如果改了slug，显示在url里面的slug还是不会变的，当然这个无所谓了，不改不就行了，哈哈哈哈哈~
        if from_edit:
            slug = urllib.parse.unquote(slug)
            post = Post.get_by_id('_' + slug)
            post.tags = []
        else:
            if slug.strip() == '':
                slug = request.form['title']
            slug = urllib.parse.unquote(slug).replace(' ', '-')
            conflicted_count = Post.get_by_id('_' + slug)
            if conflicted_count:
                slug += '-2'
            post = Post(id='_' + slug)
            post.slug = slug

        post.content = request.form['content']

        if not post.isPage:
            post.title = request.form['title']
            tags = request.form['tags']
            if request.form['post_private_flag'] == 'True':
                post.isPrivate = True
            else:
                post.isPrivate = False
            if tags and tags.strip() != '':
                for tagName in [n.strip() for n in tags.split(',')]:
                    tag = Tag.get_by_id('_' + tagName)
                    if not tag:
                        tag = Tag(name=tagName, id='_' + tagName)
                        tag.put()
                    post.tags.append(tag.key)

        post.put()

        if not from_edit:
            googlePingSrv = ServerProxy("http://blogsearch.google.com/ping/RPC2 ")
            url = request.url
            base_url = url[:url.find('/', 8)]  # 8 for https
            try:
                resp = googlePingSrv.weblogUpdates.extendedPing(
                    'wokanblog',
                    base_url,
                    base_url,  # 需要检查更新的页面URL
                    base_url + '/feed'
                )
                if resp['flerror']:
                    logging.error(resp['message'])
            except Error as v:
                logging.error(v)

        memcache.delete('getAllKeys')
        memcache.delete('queryPostFeed')
        memcache.delete('getGroupedCount')
        memcache.delete('getTagCounts')
        if not post.isPage:
            return url_for('blog.show_home')
        else:
            redirect(post.makeLink())


@bp.route('/uploadImg/', methods=['GET', 'POST'])
@login_required
def upload_image():
    if request.method == 'GET':
        return make_response('''<html><body><form method="post" enctype="multipart/form-data" >
            <p><input type="file" name="file"/></p>
            <p>裁剪：<input type="text" name="w" value="%d"/></p>
            <p><input type="submit" value="上传" /></p>
            </form></body></html>''' % util.MAX_IMG_WIDTH)
    else:
        stream = request.form['file']
        name = request.args['file'].filename
        widthLimit = int(request.form['w'])
        d = date.today()
        name = '%d_%d_%d_%s' % (d.year, d.month, d.day, name)
        img = Image(src='', name=name, id='_' + name, data=db.Blob(stream))
        img.put()

        google_img = images.Image(stream)
        if google_img.width > widthLimit:
            h = google_img.height * widthLimit / google_img.width
            stream = images.resize(stream, widthLimit, h)
            dotPos = name.rfind('.')
            ext = name[dotPos:]
            name = name[:dotPos] + '_resized' + ext
            resized_img = Image(src='', name=name, id='_' + name, data=db.Blob(stream))
            resized_img.put()

        # 如果缩放过，返回缩略图的路径，让客户端反推原图的路径
        return render_template('upload_image_done.html', name='/img/%s' % name)


"""
class ListComments(webapp.RequestHandler):
    def get(self, page):
        SIZE=30
        comments=Comment.query()
        page=1 if not page else int(page)
        pageCount=int(math.ceil(float(comments.count()) / SIZE))
        comments=comments.order(-Comment.date).fetch(SIZE, offset = (page - 1) * SIZE)
        mylookup=TemplateLookup(directories = [os.path.join(os.path.dirname(__file__), 'template')])
        template=mylookup.get_template('manage_comments.html')
        # 分页
        rg=[]
        if pageCount <= 4:
            rg=list(range(pageCount, 0, -1))
        else:
            if page >= 3 and page <= pageCount - 2:
                rg=list(range(page + 2, page - 3, -1))
            elif page < 3:
                rg=list(range(page + 2, 0, -1))
            else:
                rg=list(range(pageCount, page - 3, -1))
        # 如果缩放过，返回缩略图的路径，让客户端反推原图的路径
        # 请求来源
        _r, ccode=util.is_from_civilization(request)
        args={
            'comments': comments, 'pageCount': pageCount, 'currentPage': page, 'rg': rg,
            'pagePath': '/admin/comments/', 'ccode': ccode
        }
        response.out.write(template.render_unicode(**args))
"""


@ bp.route('/comments/report/<id>')
@login_required
def report_spam(id):
    c_key = ndb.Key(urlsafe=id)
    c = c_key.get()
    if c:
        c.status = 'spam'
        c.put()
        memcache.delete('getLatestComments')
        return make_response('ok')
    else:
        return make_response('Comment %s not found' % id)


@ bp.route('/comments/markham/<id>')
@login_required
def reverse_spam(id):
    c_key = ndb.Key(urlsafe=id)
    c = c_key.get()
    if c:
        c.status = 'approved'
        c.put()
        memcache.delete('getLatestComments')
        return make_response('ok')
    else:
        return make_response('Comment %s not found' % id)
