import os, Cookie, sys, hashlib

# Google App Engine imports.
import wsgiref.handlers
from google.appengine.ext import webapp
from google.appengine.ext import db

# Remove the standard version of Django.
for k in [k for k in sys.modules if k.startswith('django')]:
    del sys.modules[k]

# Force sys.path to have our own directory first, in case we want to import
# from it.
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Must set this env var *before* importing any part of Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

# New Django imports
from django.template.loader import render_to_string
from django.conf import settings

# Configure dir with templates
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__),'templates')
settings.configure(TEMPLATE_DIRS = (TEMPLATE_DIR,'') )

# Define page id for top-level page (i.t. Home page)
def get_home_id():
    try:
        return PageModel.gql("WHERE is_home=true")[0].key().id()
    except:
        #return None
        render_page(handler,"_login.htm",{'error': 'No main page, <a href="/setup/">create main page</a>?'})

def render_page(handler, template_name = 'default.htm', values = { }):
    output = render_to_string(template_name,values)
    handler.response.out.write(output)
    
class PageModel(db.Model):
    title = db.StringProperty()
    url =  db.StringProperty()
    content = db.TextProperty()
    reference = db.SelfReferenceProperty()
    created = db.DateTimeProperty(auto_now_add = True)
    modified = db.DateTimeProperty(auto_now = True)
    template = db.StringProperty()
    position = db.IntegerProperty()
    hidden = db.BooleanProperty()
    is_home = db.BooleanProperty()
    allow_comments = db.BooleanProperty()
    comments_number = 0 
    #historical = db.BooleanProperty()
    #user = db.UserProperty(auto_current_user = True)    
    type = db.StringProperty()
    
class CommentModel(db.Model):
    content = db.TextProperty()
    reference = db.ReferenceProperty()
    created = db.DateTimeProperty(auto_now_add = True)
    user = db.StringProperty()
    registered = db.BooleanProperty()
    
class AdminModel(db.Model):
    login = db.TextProperty()
    password_sha1 = db.TextProperty()


def set_cookie(handler, key, value):
    cookie = Cookie.SimpleCookie()
    cookie[key] = value 
    cookie[key]["path"] = "/" 
    cookie[key]["max-age"] = 60 * 60 * 24 * 7
    handler.response.headers.add_header('Set-Cookie',cookie.output()[11:])
    
def get_cookie(key):
    return Cookie.SimpleCookie(os.environ.get('HTTP_COOKIE', ''))

def sha1(s):
    return hashlib.sha1(s).hexdigest()
    
def authorize():
    if sha1("ADMIN") in str(get_cookie('session')):
        return True
    else:    
        return False

def get_requested_page_id(handler):
    s = handler.request.path
    if s.endswith('/'): 
        return get_home_id()
    last = s.split('/')[-1]
    if last.isdigit():
        try:
            return PageModel.get_by_id(int(last)).key().id()
        except AttributeError: # no such id in db
            pass
    try:
        id = PageModel.all().filter('url =', last).fetch(limit=1)[0].key().id()
        return id
    except IndexError: # no such url in db
        render_page(handler, '_404.htm')
        #return None

def get_appropriate_position(reference):
    try:
        max_position = PageModel.gql('WHERE reference=:reference ORDER BY position DESC', reference=reference)[0].position
        for position in range(1,max_position+10):
            try:
                if None==PageModel.gql('WHERE reference=:reference AND position=:position', reference=reference, position=position)[0]:
                    return position
            except:
                return position
    except:
        return 1

#
# /setup/*
#
class SetupHandler(webapp.RequestHandler):

    def get(self):
        if 0 == AdminModel.all().count() or authorize():
            
            if '' != self.request.path[7:]:
                login, n, password = self.request.path[7:].partition('/')
                new_admin = AdminModel(login=login, password_sha1=sha1(password))
                new_admin.put()
                render_page(self,"_login.htm",{'error': 'User '+login+' was created.'})
            else:
                new_page = PageModel(title = 'main page', 
                                    url = 'main',
                                    content = 'No content yet.',
                                    template = 'default.htm',
                                    position = 1,
                                    hidden=True, 
                                    allow_comments=False, 
                                    is_home=True)
                new_page.put()
                self.redirect('/edit/'+str(new_page.key().id()))
    
#
# /create_page
#
class CreateHandler(webapp.RequestHandler):

    def get(self):
        if authorize():
            new_page = PageModel(title = 'untitled', 
                                url = 'untitled',
                                content = 'No content yet.',
                                template = 'default.htm',
                                position = get_appropriate_position(PageModel.get_by_id(get_home_id()).key()),
                                hidden=True, 
                                allow_comments=True, 
                                reference=PageModel.get_by_id(get_home_id()),
                                is_home=False)
            new_page.put()
            self.redirect('/edit/'+str(new_page.key().id()))

#
# /post-comment/.*
#
class CommentHandler(webapp.RequestHandler):

    def post(self):
        
        page_id = get_requested_page_id(self)
        if page_id is None: return # error 404
        
        new_comment = CommentModel()
        
        new_comment.content = self.request.get('content').replace('<','&lt;').replace('>','&gt;').replace('\n','<br/>').replace(' ','&nbsp;')
        
        if new_comment.content != '':
            new_comment.user = self.request.get('user')
            if new_comment.user == '' or new_comment.user == 'Your name...':
                new_comment.user = 'Guest'
            #set_cookie(self,'guest-name',COMM.user)
                
            new_comment.reference = PageModel.get_by_id(page_id)
            new_comment.registered = authorize()
            new_comment.put()
            
        self.redirect('/'+str(page_id))
        
#
# /login
#
class LoginHandler(webapp.RequestHandler):

    def post(self):
        
        login = self.request.get('login')
        password_sha1 = sha1(self.request.get('password'))

        admins = db.GqlQuery("SELECT * FROM AdminModel")
        for admin in admins:
            if admin.password_sha1 == password_sha1 and admin.login == login:
                set_cookie(self,'session', sha1("ADMIN"))
                self.redirect('/')
                break
            else:
                set_cookie(self,'session', sha1("NOT ADMIN"))
                render_page(self,"_login.htm",{'error':'Wrong login or password'})
            #self.redirect('/login')
        
    def get(self):   
        render_page(self,"_login.htm")

#
# /logout
#
class LogoutHandler(webapp.RequestHandler):

    def get(self):   
        set_cookie(self,'session','bla-bla-bla')
        self.redirect('/')

#
# /delete/.*
#
class DeleteHandler(webapp.RequestHandler):

    def get(self):
        if authorize():
            #page_id = int(self.request.path[8:]) # path: /delete/1
            page_id = get_requested_page_id(self)
            if page_id is None: return # error 404
            
            CP = PageModel.get_by_id(page_id)
            db.delete(CP)
            self.redirect('/')

#
# /.*
#
class MainHandler(webapp.RequestHandler):

    def get(self):
        #if authorize():
        page_id = get_requested_page_id(self)
        if page_id is None: return # error 404
                    
        CP = PageModel.get_by_id(page_id)
        
        L0 = PageModel.get_by_id(get_home_id())    
        
                
        if authorize():
            query = "WHERE reference = :reference ORDER BY position"
        else:
            query = "WHERE reference = :reference AND hidden = False ORDER BY position"
            if L0.hidden:
                render_page(self,"_unavailable.htm")
                return
            if CP.hidden:
                render_page(self,"_404.htm")
                return
            
        comment_query = "WHERE reference = :reference"
        
        L0.number_of_comments = CommentModel.gql(comment_query, reference = L0.key()).count()
        CP.number_of_comments = CommentModel.gql(comment_query, reference = CP.key()).count()
        
        L1 = PageModel.gql(query, reference = L0.key())
        L2 = []
        #L2C = []
        for i,n in enumerate(L1):
            L1[i].number_of_comments = CommentModel.gql(comment_query, reference = L1[i].key()).count()
            L2.extend(PageModel.gql(query, reference = L1[i].key()))
            
        L3 = []
        for i,n in enumerate(L2):
            L2[i].number_of_comments = CommentModel.gql(comment_query, reference = L2[i].key()).count()
            L3.extend(PageModel.gql(query, reference = L2[i].key()))
            
        COMM = CommentModel.gql("ORDER BY created")#.fetch(1000)
        #COMM = CommentModel.
        
        render_page(self,CP.template,
        {'CP':CP,'L0':L0,'L1':L1,'L2':L2,'L3':L3,'COMM':COMM,'authorize':authorize()})

#
# /edit/.*
#
class EditHandler(webapp.RequestHandler):

    def get(self):
        if authorize():
            page_id = get_requested_page_id(self)
            if page_id is None: return # error 404
            
            CP = PageModel.get_by_id(page_id)
            L0 = PageModel.get_by_id(get_home_id())
            L1 = PageModel.gql("WHERE reference = :ref ORDER BY position", ref = L0.key())
            L2 = []
            for i,n in enumerate(L1):
                L2.extend(PageModel.gql("WHERE reference = :ref ORDER BY position", ref = L1[i].key()))
                       
            render_page(self,"_edit.htm",
            {'CP':CP,'L0':L0, 'L1':L1, 'L2':L2, 'authorize':authorize()})

    def post(self):
        if authorize():
            page_id = get_requested_page_id(self)
            if page_id is None: return # error 404
            
            page = PageModel.get_by_id(int(page_id))
            page.title = self.request.get('title')
            page.url = self.request.get('url') 
            page.content = self.request.get('content')
            page.type = self.request.get('type')
            #page.position = int(self.request.get('position'))
            page.template = self.request.get('template')
            if ".htm" not in page.template: 
                page.template = "default.htm"       
            
            if self.request.get('reference') != '':
                page_reference_id_new = int(self.request.get('reference'))
                page_reference_new = PageModel.get_by_id(page_reference_id_new)
                
                
                if not page.reference or page.reference.key().id() != page_reference_id_new:
                    page.reference = page_reference_new
                    page.position = get_appropriate_position(page_reference_new)
                else:
                    page.position = int(self.request.get('position'))
        
                #CP.reference = PageModel.get_by_id(int(self.request.get('reference')))
            
            if self.request.get('is_home') == 'on':
                page.is_home = True
            else:
                page.is_home = False
            
            if self.request.get('hidden') == 'on':
                page.hidden = True
            else:
                page.hidden = False
                                    
            if self.request.get('comments') == 'on':
                page.allow_comments = True
            else:
                page.allow_comments = False
            
            page.put()
            self.redirect('/'+str(page.url))

def main():
    application = webapp.WSGIApplication([
        ('/create_page', CreateHandler),
        ('/setup/.*', SetupHandler),
        ('/login', LoginHandler),
        ('/logout', LogoutHandler),
        ('/delete/.*', DeleteHandler),
        ('/edit/.*', EditHandler),
        #('/increment-position/.*', EditHandler),
        #('/edit/.*', EditHandler),
        ('/post-comment/.*', CommentHandler),
        ('/.*', MainHandler)],
        debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
    main()
