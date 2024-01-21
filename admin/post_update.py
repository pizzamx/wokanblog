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

import os
import urllib
import logging
import util

from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import images

from model import Post, Tag, Image

from mako.lookup import TemplateLookup

from xmlrpclib import ServerProxy, Error
from datetime import date


class NewPost(webapp2.RequestHandler):
    def get(self):
        mylookup = TemplateLookup(
            directories=[os.path.join(
                os.path.dirname(__file__),
                'template'),
                os.path.join(
                os.path.dirname(__file__),
                '../../post/template')])
        template = mylookup.get_template('post_new.html')
        tags = Tag.query()
        # 请求来源
        _r, ccode = util.is_from_civilization(self.request)
        self.response.out.write(template.render_unicode(tags=tags, ccode=ccode))

    def post(self):
        slug = self.request.get('slug')
        fromEdit = self.request.get('edit') == 'true'

        # TODO: 因为用slug做了key，所以如果改了slug，显示在url里面的slug还是不会变的，当然这个无所谓了，不改不就行了，哈哈哈哈哈~
        if fromEdit:
            slug = urllib.unquote(slug)
            post = Post.get_by_id('_' + slug)
            post.tags = []
        else:
            if slug.strip() == '':
                slug = self.request.get('title')
            slug = urllib.unquote(slug).replace(' ', '-')
            conflictedCount = Post.get_by_id('_' + slug)
            if conflictedCount:
                slug += '-2'
            post = Post(id='_' + slug)
            post.slug = slug

        post.content = self.request.get('content')

        if not post.isPage:
            post.title = self.request.get('title')
            tags = self.request.get('tags')
            if self.request.get('post_private_flag') == 'True':
                post.isPrivate = True
            else:
                post.isPrivate = False
            if tags and tags.strip() != '':
                for tagName in map(lambda n: n.strip(), tags.split(',')):
                    tag = Tag.get_by_id('_' + tagName)
                    if not tag:
                        tag = Tag(name=tagName, id='_' + tagName)
                        tag.put()
                    post.tags.append(tag.key)

        post.put()

        """
        if not fromEdit:
            googlePingSrv = ServerProxy("http://blogsearch.google.com/ping/RPC2 ")
            url = self.request.url
            baseUrl = url[:url.find('/', 8)]  # 8 for https
            try:
                resp = googlePingSrv.weblogUpdates.extendedPing(
                    'wokanblog',
                    baseUrl,
                    baseUrl,  # 需要检查更新的页面URL
                    baseUrl + '/feed'
                )
                if resp['flerror']:
                    logging.error(resp['message'])
            except Error, v:
                logging.error(v)
        """
                
        memcache.delete('getAllKeys')
        memcache.delete('queryPostFeed')
        memcache.delete('getGroupedCount')
        memcache.delete('getTagCounts')
        if not post.isPage:
            self.redirect('/')
        else:
            self.redirect(post.makeLink())


class Edit(webapp2.RequestHandler):
    def get(self, y, m, slug):
        slug = unicode(urllib.unquote(slug), 'utf-8')
        post = Post.get_by_id('_' + slug)

        mylookup = TemplateLookup(
            directories=[os.path.join(
                os.path.dirname(__file__),
                'template'),
                os.path.join(
                os.path.dirname(__file__),
                '../../post/template')])
        template = mylookup.get_template('post_new.html')
        tags = Tag.query()
        # 请求来源
        _r, ccode = util.is_from_civilization(self.request)
        self.response.out.write(template.render_unicode(tags=tags, post=post, ccode=ccode))


class NewImg(webapp2.RequestHandler):
    def get(self):
        self.response.out.write(u'''<html><body><form method="post" enctype="multipart/form-data" >
            <p><input type="file" name="file"/></p>
            <p>裁剪：<input type="text" name="w" value="%d"/></p>
            <p><input type="submit" value="上传" /></p>
            </form></body></html>''' % util.MAX_IMG_WIDTH)

    def post(self):
        stream = self.request.get("file")
        name = self.request.params['file'].filename
        widthLimit = int(self.request.get('w'))
        d = date.today()
        name = '%d_%d_%d_%s' % (d.year, d.month, d.day, name)
        img = Image(src='', name=name, id='_' + name, data=db.Blob(stream))
        img.put()

        gImg = images.Image(stream)
        if gImg.width > widthLimit:
            h = gImg.height * widthLimit / gImg.width
            stream = images.resize(stream, widthLimit, h)
            dotPos = name.rfind('.')
            ext = name[dotPos:]
            name = name[:dotPos] + '_resized' + ext
            resizedImg = Image(src='', name=name, id='_' + name, data=db.Blob(stream))
            resizedImg.put()

        mylookup = TemplateLookup(directories=[os.path.join(os.path.dirname(__file__), 'template')])
        template = mylookup.get_template('upload_image_done.html')
        # 如果缩放过，返回缩略图的路径，让客户端反推原图的路径
        self.response.out.write(template.render_unicode(name='/img/%s' % name))
