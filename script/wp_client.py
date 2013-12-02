import httplib, urllib, time

#host = 'localhost:8080'
#interval = 0

#host = 'lab.wokanxing.info'
#interval = 10

host = 'ctp.latest.lazybonereborn.appspot.com'
interval = 10

class Worker(urllib.FancyURLopener):
    def __init__(self, *args, **kwargs):
        urllib.FancyURLopener.__init__(self, *args, **kwargs)
        self.index = kwargs.get('index')

    def work(self):
    	self.open('%s/wp/%s' % (host, self.index))
    	self.read()
    	
    def http_error_default(self, url, fp, errcode, errmsg, headers):
    	print 'get %index FAILED' % index

if __name__ == '__main__':
    
    f = urllib.urlopen('http://%s/wp/count' % host)
    ids = f.read()
    print 'list: %s' % ids
    
    for i in ids.split(','):
        print 'Ready for %s' % i
        urllib.urlopen('http://%s/wp/%s' % (host, i))
        """
        conn = httplib.HTTPConnection(host)
        conn.request("GET", "/wp/%s" % i)
        r = conn.getresponse()
        if r.status == 200:
        	print 'get %03d [OK]' % int(i)
        else:
        	print 'get %03d [FAILED:%d]' % (int(i), r.status)
        #not sure about minimum value
"""
        time.sleep(interval)
