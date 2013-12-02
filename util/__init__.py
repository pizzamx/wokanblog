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

from google.appengine.api import memcache
from google.appengine.ext import webapp

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

from util.plugins import after_html_filtered

import logging, re

POST_PER_PAGE = 10
POST_PER_PAGE_FOR_HANDSET = 2
MAX_IMG_WIDTH = 600

SMILEYS = dict(((':mrgreen:', 'mrgreen'), (':neutral:', 'neutral'), (':twisted:', 'twisted'), (':arrow:', 'arrow'), (':shock:', 'eek'), 
                (':smile:', 'smile'), (':???:', 'confused'), (':cool:', 'cool'), (':evil:', 'evil'), (':grin:', 'biggrin'), (':idea:', 'idea'), 
                (':oops:', 'redface'), (':razz:', 'razz'), (':roll:', 'rolleyes'), (':wink:', 'wink'), (':cry:', 'cry'), (':eek:', 'surprised'), 
                (':lol:', 'lol'), (':mad:', 'mad'), (':sad:', 'sad'), ('8-)', 'cool'), ('8-O', 'eek'), (':-(', 'sad'), (':-)', 'smile'), 
                (':-?', 'confused'), (':-D', 'biggrin'), (':-P', 'razz'), (':-o', 'surprised'), (':-x', 'mad'), (':-|', 'neutral'), 
                (';-)', 'wink'), ('8)', 'cool'), ('8O', 'eek'), (':(', 'sad'), (':)', 'smile'), (':?', 'confused'), (':D', 'biggrin'), 
                (':P', 'razz'), (':o', 'surprised'), (':x', 'mad'), (':|', 'neutral'), (';)', 'wink'), (':!:', 'exclaim'), (':?:', 'question')))
SMILEY_PATTERNS = []
SMILEY_CLASS = []
for (code, name) in SMILEYS.iteritems():
    SMILEY_PATTERNS.append(re.compile(r'(\s|^)%s(\s|$|(</)|(\[/))' % re.escape(code), re.IGNORECASE))
    SMILEY_CLASS.append('smiley_%s' % name)

def memcached(t):
    "decorate cachable calls"
    def w(func):
        def wrapper(self, *args):
            #so func_name should be unique
            cachedData = memcache.get(func.func_name)
            if cachedData is not None:
                #logging.debug('%s hit', func.func_name)
                return cachedData
            
            logging.debug('%s missed', func.func_name)
            cachedData = func(self, *args)
            if t == -1:
                memcache.add(func.func_name, cachedData)
            else:
                memcache.add(func.func_name, cachedData, t)
            return cachedData
        return wrapper
    return w

def filter_html(func):
    def newline2p(self, *args):
        c = func(self, *args)

        #replace smileys
        i = 0
        for pattern in SMILEY_PATTERNS:
            c = pattern.sub(r'<span class="smiley %s">&nbsp;</span>\2' % SMILEY_CLASS[i], c)
            i += 1
            
        #代码加亮
        if re.search(r'(?mis)<pre.*?>.*?</pre>', c):
        	c = re.sub(r'(?mis)<pre lang="(.*?)">(.*?)</pre>', hl, c)

        #@see function wpautop in http://core.trac.wordpress.org/browser/trunk/wp-includes/formatting.php    
        c += '\n'
        c = re.sub(r'<br />\s*<br />', '\n\n', c)
        allblocks = '(?:table|thead|tfoot|caption|colgroup|tbody|tr|td|th|div|dl|dd|dt|ul|ol|li|pre|select|form|map|area|blockquote|address|math|style|input|p|h[1-6]|hr)'
        c = re.sub(r'(<%s[^>]*>)' % allblocks, r'\n\1', c)
        c = re.sub(r'(</%s>)' % allblocks, r'\1\n\n', c)
        c = c.replace('\r\n', '\n').replace('\r', '\n')   #cross-platform newlines
        c = re.sub(r'\n\n+', '\n\n', c) #take care of duplicates
        cs = re.split(r'\n\s*\n', c)
        c = ''
        for tc in cs:   #make paragraphs, including one at the end
            c += '<p>' + re.sub(r'(?ms)\n*(.*?)\n*', r'\1', tc) + '</p>\n'
        #c = re.compile(r'\n?(.+?)(?:\n\s*\n|\Z)', re.DOTALL).sub(r'<p>\1</p>\n', c) 
        c = re.sub(r'<p>\s*</p>', '', c)   #under certain strange conditions it could create a P of entirely whitespace
        c = re.sub(r'<p>([^<]+)\s*?(</(?:div|address|form)[^>]*>)', r'<p>\1</p>\2', c)
        #c = re.sub(r'<p>', r'\1<p>', c)
        c = re.sub(r'<p>(<li.+?)</p>', r'\1', c)    #problem with nested lists
        c = re.sub(r'(?i)<p><blockquote([^>]*)>', r'<blockquote\1><p>', c)
        c = c.replace(r'</blockquote></p>', r'</p></blockquote>')
        #c = re.sub(r'<p>\s*(</?%s[^>]*>)\s*</p>' % allblocks, r'\1', c) #don't pee all over a tag
        #c = re.compile(r'\n?(.+?)(?:\n\s*\n|\Z)', re.DOTALL).sub(r'<p>\1</p>\n', c)
        c = re.sub(r'<p>\s*(</?%s[^>]*>)' % allblocks, r'\1', c)
        c = re.sub(r'(</?%s[^>]*>)\s*</p>' % allblocks, r'\1', c)
        c = re.sub(r'<br />(\s*</?(?:p|li|div|dl|dd|dt|th|pre|td|ul|ol)[^>]*>)', r'\1', c)
        
        return after_html_filtered(c)
    return newline2p
    
def hl(match):
    lexer = get_lexer_by_name(match.group(1), stripall=True)
    formatter = HtmlFormatter(lineseparator='<br/>')
    return highlight(match.group(2), lexer, formatter)

def countPosts():
    "http://docs.google.com/Present?docid=ddfdgz6g_1671hhdnddc4"
