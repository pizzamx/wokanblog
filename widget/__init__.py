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

from datetime import date, timedelta, datetime
from xml.etree import ElementTree
from xml.parsers.expat import ExpatError
from collections import defaultdict

from model import Post, Image, Comment, Tag, Blogroll, CST, UTC
from util import memcached

import calendar, re, operator, urllib2, logging, time

class Calendar(object):
    def __init__(self, fromPath):
        m = re.match(r'.*/(\d{4})/(?:(\d{1,2})/)?(?:(\d{1,2})/)?.*', fromPath, re.IGNORECASE)
        if m:
            items = m.groups()
            year = int(items[0])
            if items[2] is not None or items[1] is not None:
                self.srcDay = date(year, int(items[1]), 1)
                showToday = False
            else:
                self.srcDay = date.today()
                showToday = True
        else:
            self.srcDay = date.today()
            showToday = True
        c = calendar.Calendar()
        cdays = c.itermonthdays(self.srcDay.year, self.srcDay.month)
        self.days = []
        
        groupedCount = self.getGroupedCount()
        for day in cdays:
            if day:     #去掉占位符0
                count = groupedCount[date(self.srcDay.year, self.srcDay.month, day)]
                if count:
                    if showToday and day == self.srcDay.day:
                        dclz = 'today'
                    else:
                        dclz = ''
                        
                    if len(self.days) == 0:
                        dclz += ' first_day'
                    #elif day == calendar.monthrange(self.srcDay.year, self.srcDay.month)[1]:
                        #dclz += ' last_day'
                        
                    self.days.append((day, dclz, count))
                    
        if len(self.days):
            t = self.days[-1]
            self.days.remove(t)
            self.days.append((t[0], t[1] + ' last_day', t[2])) 
    
    def dump(self):
        #monthImgUrl = self.getMonthImg(self.srcDay.year, self.srcDay.month)
        template = u"""
            <div id="calendar">
                <a href="%s" title="%s" class="month_link prev_month_link">&lt;</a><a href="%s" title="%s" class="month_link next_month_link">&gt;</a>
                <div class="c_month">%d.%d</div>
                <div class="c_days">
                    %s
                </div>
            </div>
        """
        divs = ''
        for (day, dclaz, count) in self.days:
            if count:
                divs += u'<div class="%s"><a href="%s" class="day_with_posts" title="查看%d月%d日的文章">%s<span class="post_count">%d</span></a></div>' % (dclaz, '/%d/%d/%d/' % (self.srcDay.year, self.srcDay.month, day), self.srcDay.month, day, day, count)
            else:
                pass
                #divs += '<div class="%s"><span class="normal_day">%s</span></div>' % (dclaz, day)
                
        y, m = (self.srcDay.year, self.srcDay.month)
        py, pm = (y if m > 1 else y - 1, m - 1 if m > 1 else 12)
        ny, nm = (y if m < 12 else y + 1, m + 1 if m <12 else 1)
        prevUrl = '/%d/%d/' % (py, pm)
        nextUrl = '/%d/%d/' % (ny, nm)
        prevTitle = u'查看%d年%d月的文章' % (py, pm)
        nextTitle = u'查看%d年%d月的文章' % (ny, nm)
            
        return template % (prevUrl, prevTitle, nextUrl, nextTitle, self.srcDay.year, self.srcDay.month, divs)
    
    def getMonthImg(self, y, m):
        name = 'c_%d_%d' % (y, m)
        img = Image.get_by_id('_' + name)
        if img is None:
            url = 'http://www.urbanfonts.com/images/gdcolor4.php?text=%d.%d&font=../fonts/folders/jinky/JINKY.TTF&fgColor=000000&fontBGColor=E4F2FD&width=120&height=40' % (y, m)
            img = Image(src=url, name=name, id='_' + name)
            if img.fetch():
                return '/img/' + name
            else:
                return url
        else:
            return '/img/' + name

    @memcached(-1)
    def getGroupedCount(self):
         posts = Post.query(Post.isPage == False)
         groupedCount = defaultdict(int)
         for post in posts:
             groupedCount[post.date.date()] += 1
         return groupedCount
        
class RecentComment(object):
    def dump(self):
        html = u'<h2>最新的留言</h2><ul id="recent_comments">'
        for c in self.getLatestComments():
            html += '<li><a href="%s">%s</a> (%s)</li>' % (c.makeLink(), c.post.get().title, c.getAuthorLink())
        html += '</ul>'
        return html
    
    @memcached(-1)
    def getLatestComments(self):
        return Comment.query(Comment.status == 'approved').order(-Comment.date).fetch(10)
    
class TagCloud(object):
    def dump(self):
        countList = [tagPair for tagPair in self.getTagCounts() if tagPair[1] != 0]
        if not len(countList):
            return ''
        
        if len(countList) == 1:
            maxCount, minCount  = 1, 0
        else:
            maxCount, minCount  = countList[0][1], countList[-1][1]
        diff = maxCount - minCount
        if diff == 0: diff = 1
            
        minSize, maxSize = 13, 18
        
        html = u'<h2>Tags</h2><div id="tag_cloud">'
        for (name, count) in countList:
            size = (count - minCount) / diff * (maxSize - minSize) + minSize
            html += u'<a href="/tag/%s" title="%d 篇文章" style="font-size: %spx;">%s</a>\n' % (name, count, size, name)
        html += '</div>'
        return html

    @memcached(-1)
    def getTagCounts(self):
        posts = Post.query().fetch(projection=[Post.tags])
        result = {}
        for p in posts:
            for tkey in p.tags:
                tname = tkey.get().name
                if tname in result:
                    result[tname] = result[tname] + 1
                else:
                    result[tname] = 1
        return sorted(result.items(), key=operator.itemgetter(1), reverse=True)
    
class BlogUpdates(object):
    "显示blogroll的更新情况"
    def dump(self):
        brs = Blogroll.query()
        html = '<h2>Blogroll</h2><ul id="blogroll">'
        for br in brs:
            diff = datetime.now().toordinal() - br.lastUpdate.toordinal()

            if diff <= 3:
                claz = 'just_now'
            elif diff <= 15:
                claz = 'recent'
            elif diff <= 31:
                claz = 'toolong'
            else:
                claz = 'gone'

            data = (br.blogUrl, br.desc, br.name, br.desc, claz, br.lastTitle, br.lastUpdate.replace(tzinfo=UTC()).astimezone(CST()))
            html += u'<li><a href="%s" title="%s">%s</a><br>%s<div class="update_status %s" title="%s (更新于 %s)"></div></li>' % data
        return html + '</ul>'

class SearchBox(object):
    def dump(self):
        html = '<form><input type="text" id="search_box" value="Native Search Coming Soon" /></form>'
        return ''