import webapp2

from google.appengine.ext import db

from model import Comment

class batchOP(webapp2.RequestHandler):
    def get(self):
        html = """
        <html><body>%s<br/><form action='/_batch/1'><input type="text" value="%d" name="limit"/><input type="submit"/></form></body></html>
        """
        self.response.headers['Content-Type'] = 'text/html'
        try:
            l = self.request.get('limit')
            limit = 50 if l == '' else int(l)
            cs = Comment.query().fetch(limit)
            ok = 0
            if cs:
                limit = len(cs)
                for c in cs:
                    c.key.delete()
                    ok = ok + 1
                c1 = Comment.query().count()
                self.response.write(html % (('%d / %d (%d left)' % (ok, limit, c1)), limit))
        except Exception, e:
            self.response.write(repr(e)+'\n')

class batchMigrateComment(webapp2.RequestHandler):
    def get(self):
        html = """
        <html><body>%s<br/><form action='/_batch/2'><input type="text" value="%d" name="limit"/><input type="submit"/></form></body></html>
        """
        self.response.headers['Content-Type'] = 'text/html'
        try:
            #c1 = Comment.query(Comment.post!=None).count()
            #c2 = Comment.query().count()
            l = self.request.get('limit')
            limit = 50 if l == '' else int(l)
            cs = Comment.query(Comment.post!=None).order(Comment.post, -Comment.date).fetch(limit)
            ok = 0
            if cs:
                limit = len(cs)
                for c in cs:
                    newC = Comment(parent=c.post)
                    newC.authorName = c.authorName
                    newC.authorEmail = c.authorEmail
                    newC.url = c.url
                    newC.ip = c.ip
                    newC.content = c.content
                    newC.status = c.status
                    newC.date = c.date
                    newC.put()
                    c.key.delete()
                    ok = ok + 1
                c1 = Comment.query(Comment.post!=None).count()
                self.response.write(html % (('%d / %d (%d left)' % (ok, limit, c1)), limit))
        except Exception, e:
            self.response.write(repr(e)+'\n')

application = webapp2.WSGIApplication([
    ('/_batch/1', batchOP),
    ('/_batch/2', batchMigrateComment)
], debug=False)

