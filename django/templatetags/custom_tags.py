import urllib
from google.appengine.api import urlfetch
from django import template
from django.template.defaultfilters import stringfilter
#from django.template import register
from string import Template
register = template.Library()

@register.filter
@stringfilter
def custom_cut(value, arg):
    """
    Truncates the string when the argument is found
    """
    #safe = isinstance(value, SafeData)
    
    value = value[:value.find(arg)]
    
    #if safe and arg != ';':
    #    return mark_safe(value)
    return value
#cut = stringfilter(cut)


@register.filter
@stringfilter
def custom_googledocs(v):
    """
    Find embedded google docs (iframe elements) and re-embedd them directly (without iframes)
    """
    
    def generate_embedded_doc(doc_id):
        url = "https://docs.google.com/document/pub?id=" + doc_id + "&embedded=true"
         #urllib.urlopen(url).read()
        result = urlfetch.fetch(url)
        if result.status_code == 200:
            src = result.content
        else:
            src = "fuck!" + str(result.status_code) + url
            
        return src #str(doc_id) #
    
    
    before_id = '<iframe src="https://docs.google.com/document/pub?id='
    after_id = '&amp;embedded=true"></iframe>'
    doc_id = 'no'
    
    while v.find(before_id) != -1:
        doc_id = v[v.find(before_id)+len(before_id):v.find(after_id)];
        v = v[0:v.find(before_id)] + generate_embedded_doc(doc_id) + v[v.find(after_id)+len(after_id):]
        #print doc_id
    
    # Get a file-like object for a site.
    #f = urllib.urlopen("http://ya.ru")
    # NOTE: At the interactive Python prompt, you may be prompted for a username
    # NOTE: and password here.
    # Read from the object, storing the page's contents in 's'.
    #s = f.read()
    #f.close()
    
    #value = s

    return v #alue


@register.filter
@stringfilter
def custom_youtube(v):
    """
    Substitutes <youtube>video-id</youtube> tags with embedded video //
    width="854" height="505" 
    width="700" height="418"
    width="800" height="480"
    """
    embedded_player = Template("""
    
    
        <span class="youtube">
            <object width="854" height="505">
                <param name="movie" value="http://www.youtube.com/v/$video_id&hl=en_US&fs=1&rel=0&hd=1">
                </param>
                <param name="allowFullScreen" value="true">
                </param>
                <param name="allowscriptaccess" value="always">
                </param>
                <embed class="youtube-frame" src="http://www.youtube.com/v/$video_id&hl=en_US&showinfo=1&color2=0xFFFFFF&fs=1&rel=0&hd=1" 
                type="application/x-shockwave-flash" allowscriptaccess="always" allowfullscreen="true" width="854" height="505">
                </embed>
            </object>
        </span>
    
    
    """)
    
    while v.find("<youtube>") != -1:
        video_id = v[v.find("<youtube>")+9:v.find("</youtube>")];
        v = v[0:v.find("<youtube>")] + embedded_player.substitute(video_id=video_id) + v[v.find("</youtube>")+10:]
        #print vid
        
    return v
#cut = stringfilter(cut)













