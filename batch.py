import webapp2

from google.appengine.ext import db

from model import Comment

class batchOP(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        try:
            cs = Comment.all().filter('status =', 'spam').fetch(100)
            count = len(cs)
            db.delete(cs)
            cs = Comment.all().filter('status =', 'spam')
            self.response.write('%d / %d' % (count,cs.count()))
        except Exception, e:
            self.response.write(repr(e)+'\n')

application = webapp2.WSGIApplication([
    ('/_batch', batchOP)
], debug=False)

