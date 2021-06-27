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

#
# html段落化之后再过滤
#
import re, logging
from collections import defaultdict

REGISTERED_HTML_FILTER = []

def after_html_filtered(html):
    for filter in REGISTERED_HTML_FILTER:
        html = filter(html)
    return html

# is_empty参数表示是否标签中有内容，比如[quoter/]这种就没有
def add_html_filter(tag_name, filter_func, is_empty):
    REGISTERED_HTML_FILTER.append(lambda html:parse_shortcode(html, tag_name, filter_func, is_empty))

#借用wp里面的shortcode概念
def parse_shortcode_attr(m, is_empty):
    attrs = defaultdict(lambda: '')
    att_str = m.group(1).strip()
    for (k, v) in re.findall(r'(\w+)="(.*?)"', att_str):
        attrs[k] = v
    return attrs, '' if is_empty else m.group(2)

def parse_shortcode(html, name, filter_func, is_empty):
    if not html:
        return html
    def replace_func(m):
        attrs, content = parse_shortcode_attr(m, is_empty)
        return filter_func(attrs) if is_empty else filter_func(attrs, content)
    if is_empty:
        #FIXME: 字符问题在这里
        #logging.warning(html)
        #logging.warning(re.sub(ur'(?misu)\[%s(.*?)/\]' % name, replace_func, html))
        return re.sub(r'(?misu)\[%s(.*?)/\]' % name, replace_func, html)
    else:
        return re.sub(r'(?misu)\[%s(.*?)\](.*?)(?:\[/%s\])' % (name, name), replace_func, html)

def make_caption(attrs, content):
    "生成图片的像框，带caption"
    return """<div class="wp-caption align%s" style="width: %dpx">%s
        <p class="wp-caption-text">%s</p></div>""" % (attrs['align'], int(attrs['width']) + 10, content, attrs['caption'])

def make_quote(attrs):
    #FIXME: wrong anchor
    return '<a href="#c_%s">@%s</a>: &nbsp;' % (attrs['id'], attrs['author'])
    
add_html_filter('caption', make_caption, False)
add_html_filter('quoter', make_quote, True)

