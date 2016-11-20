#!/usr/bin/env python
""""
[MotherBot] Syntax/docbot by /u/num8lock
Desc:       Model (logic module)
version:    v.0.1
git:   

"""
import os   # for collecting local data
import re
from datetime import date, datetime
import pprint as p
import copy as cp
import random
import simplejson as json
import sqlite3
from collections import OrderedDict
from bs4 import BeautifulSoup as BS
import html2text

''' LOCAL TEST CONFIGS '''
path = '~/Google Drive/docs/python-3.5.2_docs/library/'
page = 'datetime.html'
fullpath = os.path.join(os.path.expanduser(path), page)
# descriptions = OrderedDict()

def db_query(query, db_filename, table=None, version_id=None, version_major=None, 
            version_minor=None, version_micro=None, topic=None, section=None, 
            keyword=None, url=None, header=None, body=None, footer=None):
    """ update & get DB contents 
    See for variable in SQL params: docs/library/sqlite3.html
        http://stackoverflow.com/a/1010804/6882768
        http://stackoverflow.com/a/25387570/6882768 
    Arguments:
        query: get/insert 
        db_filename: to specify which database to access
        kwargs to specify 
        >>> kwargs to variables (change this later)
        # database: activity
        date_query = kwargs.get('date_query')
        username = kwargs.get('username')
        freq = kwargs.get('frequency')
    """
    with sqlite3.connect(db_filename) as db:
        c = db.cursor()
        today = datetime.today()    
        if query == 'insert' and table == 'Library':
            print('Populating {}...'.format(table))
            datagroup = (
                version_id, version_major, version_minor, version_micro, 
                topic, section, keyword, url, header, body, footer, today
                )
            c.execute('''
                INSERT INTO Library 
                (
                version_id, version_major, version_minor, version_micro, 
                topic, section, keyword, url, header, body, footer, 
                date_created
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', datagroup)
            db.commit()

def create_db(db_filename, table):
    """Create related database and tables"""
    db_is_new = not os.path.exists(db_filename)
    if db_is_new:
        print('Need to create schema. Creating database.')
        with sqlite3.connect(db_filename) as db:
            c = db.cursor()
            today = datetime.today()
            if table == 'Library':
                print('Creating table {}...'.format(table))        
                c.execute("""
                    CREATE TABLE IF NOT EXISTS Library (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        date_created DATE, 
                        version_id INTEGER IDENTITY, 
                        version_major INTEGER, 
                        version_minor INTEGER, 
                        version_micro INTEGER,
                        topic CHAR(25), 
                        section CHAR(25), 
                        keyword CHAR(25), 
                        url TEXT, 
                        header TEXT, 
                        body TEXT, 
                        footer TEXT)
                    """)
                db.commit()
        return

    elif not db_is_new:
        print('Database exists, assume schema does, too.')
        return
    
def create_definitions(fullpath):
    """ This is the main function (class?) to initialize the definitions data 
    Arguments: ==> TODO
        URL path
        datastore: database URL
        function name and query (optional for scraping new docs) 

    Process: start by getting the doc file
        get the chuncks of sections of definition
        store to temp datastore?
        process markup conversion on each of section into parts, 
        - keyword : exact syntax
        - header: function syntax & arguments
        - body: function definition
        then gather metadata into a dict
        - metadata: section link, h1 header
        join 3 parts to a single section
        store to database
    """
    ''' Initialize data sources '''
    with open(fullpath, 'r', encoding='utf-8') as doc:
        _doc = BS(doc, 'lxml')
    datadump        = {}
    h               = html2text.HTML2Text()
    h.ignore_links  = False
    _sections       = _doc.find_all('dl')
    # in <ul class="this-page-menu"> <...><li><a href="../_sources/library/functions.txt"
    _src            = _doc.body.find(attrs={'class':'this-page-menu'})     
    _var_opt        = ''.join(_doc.head.script.contents)

    """ [ Metadata ] for naming & hyperlinks """
    """Get Python version from the page (set by javascript in header: 
    var DOCUMENTATIONS_OPTIONS) and use them for URL variables and other 
    metadata"""
    _version        = re.search(r'VERSION.*\'([\d\.]+)\'', _var_opt)
    _suffix         = re.search(r'SUFFIX.*\'(\.\w+)\'', _var_opt)
    _part           = re.search(r'\.\./_sources/([\w]+)/([\w]+)\.*', str(_src))
    # Initialize variables for metadata
    DOC_ROOT        = 'https://docs.python.org'
    DOC_LONGVERSION =_version.group(1)  # i.e. 3.5.2
    DOC_VERSION     = DOC_LONGVERSION[0]    # i.e. 3
    DOC_TOPIC       = _part.group(1)          # i.e. library, references, etc
    DOC_SECTION     = _part.group(2)        # i.e, functions, exceptions,logging
    DOC_SUFFIX      = _suffix.group(1)
    DOC_VER_URL     = '{}/{}/'.format(DOC_ROOT, DOC_VERSION)
    DOC_SECTION_URL = '{}/{}/{}/'.format(DOC_ROOT, DOC_VERSION, DOC_TOPIC)
    DOC_FULL_URL = '{}/{}/{}/{}{}'.format(
                    DOC_ROOT, DOC_VERSION, DOC_TOPIC, DOC_SECTION, DOC_SUFFIX)
    if _part.group(1) == (DOC_ROOT or fullpath) and DOC_SECTION == 'glossary':
        DOC_TOPIC = 'glossary'

    """ SETUP database (json ?)
    DB : See DocBot_Schema.sql  
    """
    # There's another database for analytic & logging purposes
    db_table      = DOC_TOPIC.capitalize()  
    version_id    = ''.join(DOC_LONGVERSION.split('.'))
    version_major = version_id[0]
    version_minor = version_id[1]
    version_micro = version_id[2]

    def transform_relative_links(arg):
        """ Replaces internal anchor refs and relative urls with abs path """
        try:
            def subpattern(match):
                if match.group(1):
                    return r'{}{}'.format(DOC_FULL_URL, match.group(1))
                elif match.group(2):
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
        # This might be the wrong way to catch exception
        except re.error as exception:
            print(exception)
            return False

    def markdown_header(arg):
        """ For marking up headers in definition headers """
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
        return identifiers[arg]

    def fix_space_in_html(bstag, htmltag, css):
        """ Fix annoying trailing space in <em>class </em> to avoid
        incorrect markdown formatting"""
        for tag in bstag.find_all(htmltag, {'class': css}):
            next_txt = tag.next_sibling.string
            # unwrap the sibling to avoid double markup
            tag.next_sibling.unwrap()
        return bstag

    def section_keyword(section):
        ''' [ Keywords ] Evaluate if section contains valid definition '''
        dt_parent = section.dt.parent
        while 'id' in section.dt.attrs:
            keyword = section.dt.attrs['id']
            # print('id key: {0}'.format(keyword))
            return keyword
        if section.dt.code.next_sibling:
            # print('start looking in class')
            first = section.dt.code.text
            second = section.dt.code.next_sibling.string
            # print('\n>> using first, second:', type(first), type(second))
            keyword = ''.join('{}{}'.format(first, second))
            print('class key:', type(keyword), keyword)
            return keyword
        else:
            return False

    def section_header(section):
        ''' [ Header ] sections '''
        # replace relative URLs in href to absolute path using regex
        internal_link = transform_relative_links(section.a['href'])
        if internal_link is not False:
            section.a['href'] = internal_link
            # p.pprint(header_link.__dict__)
        url = section.a['href']
        # < Hack > copy untouched section.dd 1st since we're destroying all 
        # spans & still need to manipulate them in body (section.dd) later
        store_dd = cp.copy(section.dd)
        for span in section.find_all('span'):
            span.unwrap()
        # put copy back
        section.dd = store_dd

        # Process header data from dt
        # < Hack > fix annoying trailing space in <em>class </em> to avoid 
        # incorrect markdown formatting
        for em in section.dt.find_all('em', {'class': 'property'}):
            em.string = '_{}_ '.format(em.text.strip())
            em.unwrap()
            # print('em:', em)

        # < Hack > around BS because making it output simple strings is like 
        # getting your money back from asshole you misjudged a long time ago
        transform_header = []
        for content in section.dt.contents:
            transform_header.append(str(content))
        # Format header section
        header = '{0}{1}'.format(
                markdown_header('h5'),
                h.handle(''.join(transform_header).strip()),
                )
        return header, url

    def section_body(section):
        ''' [ Body ] section '''
        # convert internal & relative url links to absolute paths
        for link in section.dd.select('a[href]'):
            if link is not None:
                transform_link = transform_relative_links(link.attrs['href'])
                link.attrs['href'] = transform_link
        transform_body =[]
        for content in section.dd.contents:
            transform_body.append(str(content))
        body = str(h.handle(''.join(transform_body).strip()))
        return body

    def section_footer(section):
        ''' [ Footer ]  '''
        # footer = apply_footer(DOC_FULL_URL) # to do
        footer = None
        return footer

    def __init__():
        """ Extract data from page """
        for section in _sections:
            if section_keyword(section):
                keyword = section_keyword(section)
                # print('got keyword:', keyword)
                header, url = section_header(section)
                # print('got header: {}\ngot url: {}'.format(header, url))
                body = section_body(section)
                # print('got body:', body)
                footer = section_footer(section)
                # print('got footer:', footer, '\n')
                ''' Store all the data '''
                keyword_dict = { 
                    'version': DOC_VERSION,
                    'version_full': DOC_LONGVERSION,
                    'topic': DOC_TOPIC,
                    'section': DOC_SECTION,
                    # 'keyword': keyword,
                    'url' : url,
                    'header': header, 
                    'body': body, 
                    'footer': footer,
                }
                # datadump[keyword] = keyword_dict.copy() # faster than update()
                print(keyword_dict)
                # create_db('DocBot_DB.db', db_table)
                '''
                db_query(
                        'insert', 'DocBot_DB.db', table=db_table, 
                        version_id=version_id, 
                        version_major=version_major, 
                        version_minor=version_minor, 
                        version_micro=version_micro, 
                        topic=DOC_TOPIC, 
                        section=DOC_SECTION, 
                        keyword=keyword, 
                        url=url,
                        header=header, 
                        body=body, 
                        footer=footer
                        )'''

    __init__()


""" Start """
create_definitions(fullpath)