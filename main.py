# encoding=utf-8
import wsgiref.handlers
import logging
import re
from google.appengine.ext import webapp
from google.appengine.api import urlfetch
from google.appengine.api import memcache
from google.appengine.ext import db

home_index = """
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<meta name="verify-v1"
	content="CNEMoyVizjTTvHbuaQUVcbBRGMmAmd9jqscFI9+l7JY=" />
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<title>Blogispot Mirror</title>
</head>
<body>
<div style="text-align: center; clear: both;  border: 1px dashed; padding: 5px 20px 5px 20px;"><form action="/" method="post">http://<input	type="text" name="stuff_url" style="border: 1px solid #000000;"	size="60">.blogspot.com/<input type="submit" style="border: 1px solid #000000;" value="GO"></form></div>
main_block
<div id="foot" style="clear: both; margin-top: 20px; width: 100%; text-align: right">
<img src="http://code.google.com/appengine/images/appengine-silver-120x30.gif"	alt="Powered by Google App Engine" />
</div>
</body>
</html>
"""

google_analytics = """
<script type="text/javascript">

  var _gaq = _gaq || [];
  _gaq.push(['_setAccount', 'UA-95317-5']);
  _gaq.push(['_trackPageview']);

  (function() {
    var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
    ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
    var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
  })();

</script>
"""
google_adsence = """
<div align="center">
<script type="text/javascript"><!--
google_ad_client = "ca-pub-1812984074023185";
google_ad_slot = "5346731860";
google_ad_width = 728;
google_ad_height = 90;
//-->
</script>
<script type="text/javascript"
src="http://pagead2.googlesyndication.com/pagead/show_ads.js">
</script>
</div>
"""
site_list = [
        'feeds.feedburner.com', 
        'twitter.com', 
        'farm1.static.flickr.com',
        'farm2.static.flickr.com',
        'farm3.static.flickr.com',
        'farm4.static.flickr.com',
        'farm5.static.flickr.com',
        'farm6.static.flickr.com',
        'farm7.static.flickr.com',
        'farm8.static.flickr.com',
        'www.ibeyond.net',
        'zh.wikipedia.org',
        'upload.wikimedia.org',
        ]

class Host(db.Model):
    url = db.StringProperty()
    title = db.StringProperty()
    update_at = db.DateTimeProperty(auto_now = True)
    create_at = db.DateTimeProperty(auto_now_add = True)

class HostCnt(db.Model):
    url = db.StringProperty()
    cnt = db.IntegerProperty()
    update_at = db.DateTimeProperty(auto_now = True)
    create_at = db.DateTimeProperty(auto_now_add = True)

class MainPage(webapp.RequestHandler):
    def get(self):
        write = self.response.out.write
        uri = self.request.uri
        url_list = uri.split('/')
        host_html = ''
        tmp_host = Host.all().order('create_at')
        if tmp_host.count() > 100:
            for tmp in tmp_host:
                tmp.delete()    

        tmp_host_cnt = HostCnt.all().order('create_at')
        if tmp_host_cnt.count() > 100:
           for tmp in tmp_host:
               tmp.delete()

        if ''.join(url_list[3:4]) == '' or ''.join(url_list[3:4]).startswith('?'):
            page_no = 1
            if not ''.join(url_list[3:4]).startswith('?'):
                results = Host.all().order('-create_at').fetch(100)
            else:
                page_no = int(self.request.get('page_no'))
                results = Host.all().order('-create_at').fetch(100 * page_no, 100)
                page_no += 1
            host_html += '<ul>'
            for result in results:
                host_html += '<li><a href="'
                host_html += result.url
                host_html += '">'
                host_html += result.title
                host_html += '</a></li>'
            host_html += '</ul>'
            host_html += '<div style="text-align: right"><a href="/?page_no=%s">Next Page</a></div>' % page_no            
            write(self.replace(home_index, {
                '<body>':'<body>' + google_adsence, 
                'main_block':'<div id="main" style="border-bottom: 1px dashed">%s</div>' % host_html,
                }) + google_analytics)
            return
        else:
            url = ('http://%s.blogspot.com/%s' % (''.join(url_list[3:4]), '/'.join(url_list[4:])))
            if ''.join(url_list[3:4]) in site_list:
                url = ('http://%s/%s' % (''.join(url_list[3:4]), '/'.join(url_list[4:])))                
            try:
                result = memcache.get(url)
                if result is not None:
                    self.response.headers['Content-Type'] = result.headers['Content-Type']
                    self.response.out.write(result.content)
                    return
                result = urlfetch.fetch(url=url,headers=self.request.headers,allow_truncated=True)
                if result.status_code == 200:
                    self.response.headers['Content-Type'] = result.headers['Content-Type']
                    if result.headers['Content-Type'].find('text/html') == -1:
                        try:
                            memcache.add(url,result,86400)
                        except:
                            pass
                        self.response.out.write(result.content)
                    else:
                        content = self.replace(result.content,
                                                    {
                                                        '></iframe>':'></iframe>' + google_adsence,
                                                    }
                                                    ) + google_analytics
                        p = re.compile(r'http://(?P<host_name>(\w|-|\.)+?).blogspot.com', re.I)
                        content = re.sub(p, r'%s://%s/\g<host_name>' % (self.request.scheme, self.request.host), content)
                        for site in site_list:
                            p = re.compile(r'https?://%s' % (site) , re.I)
                            content = re.sub(p, r'%s://%s/%s' % (self.request.scheme, self.request.host, site), content)
                            if site == 'zh.wikipedia.org':
                                content = content.replace('="/', r'="%s://%s/%s/' % (self.request.scheme, self.request.host, site))

                        self.response.out.write(content)

                        title_re = re.compile(r">(?P<title>.+?)</title>",re.I)
                        title = 'Nothing'
                        if title_re.search(content):
                            title = title_re.search(content).group('title')

                        for hosts in Host.all().filter('url =', uri):
                            hosts.delete()

                        host = Host(url = uri, title = unicode(title,'utf-8'))
                        host.put()

                        host_cnt = HostCnt.all().filter('url =', uri).get()
                        if host_cnt is None:
                            host_cnt = HostCnt(url = uri, cnt = 1)
                        else:
                            host_cnt.cnt += 1

                        host_cnt.put()

                        
                else:
                    self.response.set_status(result.status_code)
            except Exception,e:
                pass                    
        
    def replace(self,content,replace_str_dict={}):
            for k,v in replace_str_dict.items():
                content = content.replace(k,v)
            return content

    def post(self):
        self.redirect('/' + self.request.get('stuff_url'))
        return
    
def main():
    application = webapp.WSGIApplication(
                                       [('/.*', MainPage),],
                                       debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
    main()
