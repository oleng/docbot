#!/usr/bin/env python
""""
[MotherBot] Syntax/docbot by /u/num8lock
Desc:       Model (logic module)
version:    v.0.1
git:   

"""
import os   # for collecting local data
import re
import pprint as p
import copy as cp
from collections import OrderedDict
from bs4 import BeautifulSoup as BS
import html2text
import simplejson

''' LOCAL TEST CONFIGS '''
path = '~/Google Drive/docs/python-3.5.2_docs/library/'
page = 'functions.html'
fullpath = os.path.join(os.path.expanduser(path), page)
dbpath = ''
jsonpath = ''
# descriptions = OrderedDict()

def create_definitions(fullpath, datastore=None, **kwargs):
    """ This is the main class to initialize the definitions data 
    Steps:
        1. extract definition informations from local documentation copy,
        2. convert the markup to markdown
        3. store the result to a datastorage
        4. initialize the data index.
        Arguments:
        URL path
        datastore
        function name and query (optional)
        If given function as keyword arguments, it will look up return 

        start by getting the doc file
        get the chuncks of sections of definition
        store to temp datastore?
        process markup conversion on each of section into 3 parts, 
        - keyword 
        - title: function syntax & arguments
        - body: function definition
        then gather metadata into a dict
        - metadata: section link, h1 title
        join 3 parts to a single section
        store to database
    """
    def __init__():
        """
        Get Python version from the page (set by js: var DOCUMENTATIONS_OPTIONS) 
        and use them for URL variables and other metadata
        """
        ''' Initialize data sources '''
        datadump = {}
        meta = {}
        h = html2text.HTML2Text()
        h.ignore_links = False
        with open(fullpath, 'r', encoding='utf-8') as doc:
            _doc = BS(doc, 'lxml')
        # datadump.append(sections)
        _sections = _doc.find_all('dl')
        _src = _doc.body.find(attrs={'class':'this-page-menu'})
        _var_opt = ''.join(_doc.head.script.contents)

        """ [ Metadata ] for hyperlinks """
        _version = re.search(r'VERSION.*\'([\d\.]+)\'', _var_opt)
        _suffix = re.search(r'SUFFIX.*\'(\.\w+)\'', _var_opt)
        _part = re.search(r'\.\./_sources/([\w]+)/([\w]+)\.*', str(_src))
        # Initialize variables for metadata
        DOC_ROOT = 'https://docs.python.org'
        DOC_LONGVERSION =_version.group(1)
        DOC_VERSION = DOC_LONGVERSION[0]
        DOC_TOPIC = _part.group(1)
        DOC_SECTION = _part.group(2)
        DOC_SUFFIX = _suffix.group(1)
        DOC_VER_URL = '{}/{}/'.format(DOC_ROOT, DOC_VERSION)
        DOC_SECTION_URL = '{}/{}/{}/'.format(DOC_ROOT, DOC_VERSION, DOC_TOPIC)
        DOC_FULL_URL = '{}/{}/{}/{}{}'.format(
                    DOC_ROOT, DOC_VERSION, DOC_TOPIC, DOC_SECTION, DOC_SUFFIX)
        if _part.group(1) == (DOC_ROOT or fullpath) and DOC_SECTION == 'glossary':
            DOC_TOPIC = 'glossary'

        """ Setup json & database """
        # for each major version create a directory, with subdirectories for 
        # topics mirroring documentation structure, one json file per section. 
        # use one table for each topic in database
        current_dir = os.getcwd()

        def store_json(filename, directory, subdirectory):
            """ Check if directory/files exists and create one if not """
            # os.makedirs
            pass
            # return True 
        
        def internal_ref(arg):
            """ Replaces internal anchor refs and relative urls with abs path """
            try:
                def subpattern(match):
                    if match.group(1):
                        # print('<re matched group 1!> : {}{}'
                        #     .format(DOC_FULL_URL, match.group(1)))
                        return r'{}{}'.format(DOC_FULL_URL, match.group(1))
                    elif match.group(2):
                        # print('<re matched group 2!> : {}{}'
                        #     .format(DOC_SECTION_URL, match.group(2)))
                        return r'{}{}'.format(DOC_SECTION_URL, match.group(2))
                    elif match.group(3):
                        strings = match.group(3)[
                                    (match.start(3)+3): match.end()
                                    ]
                        ''' This match.span print basically just for reminder '''
                        # print('<re matched group 3> : {} : {}{}'
                        #     .format(match.span(3), DOC_VER_URL, strings)
                        #     )
                        return r'{}{}'.format(DOC_VER_URL, strings)
                    else:
                        print('{} not found :(( ', match)
                # group 1: same page ref anchor, 
                # group 2: pages in same part of doc, 
                # group 3: pages in different parts of doc
                urlsub = re.sub(
                  r'^(#[\w\.]+)|^([\w]+\.htm.[#\w.]+)|^(\.{2}/[\w+|/+]*\.htm.#.*)', 
                  subpattern, arg
                  )
                return urlsub
            except re.error as exception:
                print(exception)
                return False

        def markdown_header(arg):
            """ For marking up headers in definition titles """
            header = {'h1': '# ', 'h2': '## ', 'h3': '### ', 'h4': '#### ', 
                        'h5': '##### ', 'h6': '###### '}
            return header[arg]

        def markdown_note_changes(arg):
            """ < Hack > change some notes tagged with css classes with Markdown
            before passed to html2text and get destroyed """
            identifiers = {
                    'versionchanged': 'blockquote', 
                    'versionadded': 'blockquote', 
                    'versionmodified': 'em', 
                    'admonition-title': 'b',
                    'first': 'blockquote', 'last': 'blockquote',
                    }
            # print('[ identifier {} : {} ]'.format(arg, identifiers[arg]))
            return identifiers[arg]

        def fix_space_in_html(bstag, htmltag, css):
            """ Fix annoying trailing space in <em>class </em> to avoid
            incorrect markdown formatting"""
            # print('em:', section.dt.em)
            for tag in bstag.find_all(htmltag, {'class': css}):
                # print('strip:', em.string.replace_with('class'))
                next_txt = tag.next_sibling.string
                # print('next:', em.next_sibling.string.replace_with(
                    # " `{}`".format(next_txt)))
                # unwrap the sibling to avoid double markup
                tag.next_sibling.unwrap()
            return bstag

        """ Extract data from page """
        for section in _sections:
            ''' [ Keywords ] for query lookup   '''
            keyword = section.code.text
            
            ''' [ Title ] sections '''
            # replace relative URLs in href to absolute path using regex
            internal_link = internal_ref(section.a['href'])
            if internal_link is not False:
                section.a['href'] = internal_link
                # p.pprint(title_link.__dict__)
            url = section.a['href']
            # print('link:', url)
            # insert link for metadata
            
            # < Hack > copy untouched section.dd first since we're destroying  
            # span & we still need to manipulate them in body (section.dd) later
            store_dd = cp.copy(section.dd)
            for span in section.find_all('span'):
                span.unwrap()
            section.dd = store_dd

            # Process title data from dt
            # < Hack > fix annoying trailing space in <em>class </em> to avoid 
            # incorrect markdown formatting
            for em in section.dt.find_all('em', {'class': 'property'}):
                # print('strip:', em.string.replace_with('class'))
                next_txt = em.next_sibling.string
                # print('next:', em.next_sibling.string.replace_with(
                    # " `{}`".format(next_txt)))
                # unwrap the sibling to avoid double markup
                em.next_sibling.unwrap()
                # print('em:', em.__dict__)
            # < Hack > around BS because making it output simple strings is like 
            # getting your money back from asshole you misjudged a long time ago
            transform_title = []
            for content in section.dt.contents:
                # print('content:', content)
                transform_title.append(str(content))
            # Format title section
            title = '{0}{1}'.format(
                    markdown_header('h5'),
                    h.handle(''.join(transform_title).strip()),
                    # '\n'
                    )
            # print('title:', title.replace('¶', '^URL'))

            ''' [ Body ] section '''
            # convert internal & relative url links to absolute paths
            for link in section.dd.select('a[href]'):
                if link is not None:
                    # p.pprint(link.__dict__)
                    # print('\n(href before): {}'.format(link.attrs['href']))
                    transform_link = internal_ref(link.attrs['href'])
                    link.attrs['href'] = transform_link
                    # print(link)
            # stupid filter passes but it's easier than figuring out the right 
            # loop
            html_replacement = ['versionchanged', 'versionadded', 
                'versionmodified','admonition-title', 'first', 'last']
            # ugly hack, didn't work
            tmp = []
            for css in html_replacement:
                for tag in section.dd.find_all(['div', 'span'], attrs={'class': css}):
                    if tag:
                        tag.unwrap()

            body = section.dd
            transform_body =[]
            for content in body.contents:
                # print('x:', x)
                transform_body.append(str(content))
            body = h.handle(''.join(transform_body).strip())
            # internal_link = internal_ref(link.a['href'])
            # print('body: ::: ', body)

            footer = apply_footer(DOC_FULL_URL)

            ''' Store all the data '''
            keyword_dict = { 
                'topic': DOC_TOPIC,
                'version': DOC_VERSION,
                'version_full': DOC_LONGVERSION,
                'topic': DOC_TOPIC,
                'section': DOC_SECTION,
                'title': title, 
                'body': body, 
                'footer': footer,
                'url' : url,
            }
            datadump[keyword] = keyword_dict.copy()
            store_json(keyword, keyword_dict['topic'], keyword_dict['section'])
            # with open()
        p.pprint(datadump)


    def apply_footer(url):
        pass

    __init__()


create_definitions(fullpath)

"""
    escape_chars = { '*': '\*', '_': '\_' }

        # print(descriptions)
        # if database, double check results stored, collect the query result and 
        # return it to caller function
"""        


def dumplog(time, thread):
    scanlog.append(
        {
        'scanned': time, 
        'id': thread.id, 
        'author': thread.author,
        'created_utc': thread.created_utc,
        'permalink': thread.permalink,
        'link_title': thread.title,
        'selftext': thread.selftext,
        'num_comments': thread.num_comments
        }
    )
