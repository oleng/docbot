#!/usr/bin/env python
""""
[MotherBot] Syntax/docbot by /u/num8lock
Desc:       Model (logic module)
version:    v.0.1
git:   

"""
import os   # for collecting local data
import re
import time
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
page = 'functions.html'
fullpath = os.path.join(os.path.expanduser(path), page)
# descriptions = OrderedDict()

def db_query(query, db_filename, table, keyword):
    """ get DB contents """
    with sqlite3.connect(db_filename) as db:
        c = db.cursor()
        # cursor.execute('''
        # SELECT
        # ''')

def create_db(db_filename, db_table):
    '''Create related database and tables'''
    db_is_new = not os.path.exists(db_filename)
    if not db_is_new:
        print('Database exists, assume schema does, too.')
        return
    elif db_is_new:
        print('Need to create schema. Creating database.')
        db = sqlite3.connect(db_filename)
        c = db.cursor()
        today = date.today()
        c.execute('''
            CREATE TABLE IF NOT EXISTS ?
            (
                id INTEGER PRIMARY KEY, date_created=? DATE, 
                keyword UNIQUE CHAR(50), header TEXT, body TEXT, footer TEXT, 
                url TEXT, metadata TEXT
            )
            ''', db_table, today)
        db.commit()
    # close connection
    c.close()
    db.close()

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
    datadump = {}
    meta = {}
    h = html2text.HTML2Text()
    h.ignore_links = False
    with open(fullpath, 'r', encoding='utf-8') as doc:
        _doc = BS(doc, 'lxml')
    _sections = _doc.find_all('dl')
    _src = _doc.body.find(attrs={'class':'this-page-menu'})
    _var_opt = ''.join(_doc.head.script.contents)

    """ [ Metadata ] for naming & hyperlinks """
    """Get Python version from the page (set by javascript in header: 
    var DOCUMENTATIONS_OPTIONS) and use them for URL variables and other 
    metadata"""
    _version = re.search(r'VERSION.*\'([\d\.]+)\'', _var_opt)
    _suffix = re.search(r'SUFFIX.*\'(\.\w+)\'', _var_opt)
    _part = re.search(r'\.\./_sources/([\w]+)/([\w]+)\.*', str(_src))
    # Initialize variables for metadata
    DOC_ROOT = 'https://docs.python.org'
    DOC_LONGVERSION =_version.group(1)  # i.e. 3.5.2
    DOC_VERSION = DOC_LONGVERSION[0]    # i.e. 3
    DOC_TOPIC = _part.group(1)          # i.e. library, references, etc
    DOC_SECTION = _part.group(2)        # i.e, functions, exceptions,logging
    DOC_SUFFIX = _suffix.group(1)
    DOC_VER_URL = '{}/{}/'.format(DOC_ROOT, DOC_VERSION)
    DOC_SECTION_URL = '{}/{}/{}/'.format(DOC_ROOT, DOC_VERSION, DOC_TOPIC)
    DOC_FULL_URL = '{}/{}/{}/{}{}'.format(
                    DOC_ROOT, DOC_VERSION, DOC_TOPIC, DOC_SECTION, DOC_SUFFIX)
    if _part.group(1) == (DOC_ROOT or fullpath) and DOC_SECTION == 'glossary':
        DOC_TOPIC = 'glossary'

    """ SETUP database (json ?)
    DB : See DocBot_Schema.sql  
    """
    # There's another database for analytic & logging purposes
    database = 'Python{0}_{1}_{2}'.format(
        DOC_VERSION, DOC_LONGVERSION.strip('.')[1:], DOC_TOPIC.capitalize()
        )
    db_table = DOC_SECTION.capitalize()
    # for security, don't use variables in function executing db queries
    # define here instead
    db_filename = '{}.db'.format(database)  

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

    def apply_footer(url):
        pass

    def __init__():
        """ Extract data from page """
        for section in _sections:
            ''' [ Keywords ] for query lookup   '''
            keyword = str(section.code.text)    # force to string, got expr instead
            
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
                next_txt = em.next_sibling.string
                # unwrap the sibling to avoid double markup
                em.next_sibling.unwrap()
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

            ''' [ Body ] section '''
            # convert internal & relative url links to absolute paths
            for link in section.dd.select('a[href]'):
                if link is not None:
                    transform_link = transform_relative_links(link.attrs['href'])
                    link.attrs['href'] = transform_link
            # stupid filter passes but it's easier than figuring out the right 
            # loop
            '''ugly hack, didn't work
            html_replacement = ['versionchanged', 'versionadded', 
                'versionmodified','admonition-title', 'first', 'last']
            tmp = []
            for css in html_replacement:
                for tag in section.dd.find_all(['div', 'span'], attrs={'class': css}):
                    if tag:
                        tag.unwrap()
            '''
            transform_body =[]
            for content in section.dd.contents:
                transform_body.append(str(content))
            body = h.handle(''.join(transform_body).strip())
            ''' [ Footer ]  '''
            footer = apply_footer(DOC_FULL_URL) # to do

            ''' Store all the data '''
            keyword_dict = { 
                'keyword': keyword,
                'header': header, 
                'body': body, 
                'footer': footer,
                'url' : url,
                'metadata': {
                    'version': DOC_VERSION,
                    'version_full': DOC_LONGVERSION,
                    'topic': DOC_TOPIC,
                    'section': DOC_SECTION,
                    }
            }
            datadump[keyword] = keyword_dict.copy() # faster than update()

            print('filename: {}, table: {}'.format(db_filename, db_table))
            create_db(db_filename, db_table)
            # 'keyword'= keyword, 'header' = header, 'body'= body, 
            # 'footer'= footer, 'url'= url, 'metadata'= {
            #         'version': DOC_VERSION,
            #         'version_full': DOC_LONGVERSION,
            #         'topic': DOC_TOPIC,
            #         'section': DOC_SECTION,
            #         }

    __init__()


""" Start """
create_definitions(fullpath)