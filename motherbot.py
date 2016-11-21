#!/usr/bin/env python
""""
[MotherBot] Syntax/docbot by /u/num8lock
Desc:       Model (logic module)
version:    v.0.1
git:   

"""
import os
import re
from datetime import date, datetime
import time                             # remove later
import pprint as p                      # remove later
import copy as cp                       # to copy section
# import simplejson as json             # json store for sending data, new idea
from collections import OrderedDict
from bs4 import BeautifulSoup as BS
import html2text
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.motherdb import Library

engine = create_engine('sqlite:///database/docbot.db', echo=True)   # change to False
# create a Session
Session = sessionmaker(bind=engine)
session = Session()

def db_insert(table=None, version_id=None, version_major=None, 
            version_minor=None, version_micro=None, topic=None, section=None, 
            keyword=None, url=None, header=None, body=None, footer=None):
    """ Update database
    Arguments:
        table:          Database table name
        version_id:     Int, main variable for user <version> query
        version_major:  Int(major).x.x, i.e. 3.5.2, 2.7.12
        version_minor:  x.int(minor).x
        version_micro:  x.x.int(micro)
        topic:          Library/Activity (Python Doc **Section** & User table)
        section:        Python doc page name, based on module name
        keyword:        Main variable for user <syntax> query
        url:            Permalink to Python doc syntax definition 
        header:         Syntax & argument part
        body:           Definition part
        footer:         Related document URLs & docbot information links
    """
    # Create objects
    # if table == 'Library':
    doc = Library( 
        version_id, 
        version_major, 
        version_minor, 
        version_micro, 
        topic, 
        section, 
        keyword, 
        url, 
        header, 
        body, 
        footer
        )

    session.add(doc)
    # commit the record the database
    session.commit()

def create_definitions(fullpath):
    """ This is the main function to initialize the definitions data 
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
    _part           = re.search(r'\.\./_sources/([\w]+)/([\w.]+)\.*', str(_src))
    # Initialize variables for metadata
    DOC_ROOT        = 'https://docs.python.org'
    DOC_LONGVERSION =_version.group(1)  # i.e. 3.5.2
    DOC_VERSION     = DOC_LONGVERSION[0]    # i.e. 3
    DOC_TOPIC       = _part.group(1)          # i.e. library, references, etc
    DOC_SECTION     = os.path.splitext(_part.group(2))[0]  # i.e, functions, exceptions,logging
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
    version_micro = version_id[2:]

    def transform_relative_links(arg):
        """ Replaces internal anchor refs and relative urls with absolute path
        group 1: same page href anchor, 
        group 2: links to different page in the same Python doc section 
        group 3: links to different sections
        """
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
        """ HTML to Markdown headers """
        header = {'h1': '# ', 'h2': '## ', 'h3': '### ', 'h4': '#### ', 
                    'h5': '##### ', 'h6': '###### '}
        return header[arg]

    def section_keyword(section):
        ''' [ Keywords ] 
        - Evaluate if section contains valid definition & extract the strings
        '''
        dt_parent = section.dt.parent
        keyword = ''
        while 'id' in section.dt.attrs:
            keyword = section.dt.attrs['id']
            # print('\n>>> id key: {0}'.format(str(keyword)))
            return keyword
        try:
            if section.dt.code.next_sibling is not None:
                # print('\n>>> start looking in class')
                # print('\n>>> what are we looking here: next name', section.dt.code.__dict__)
                first = section.dt.code.text
                second = section.dt.code.next_sibling.string
                # print('\n>> using first, second:', type(first), type(second))
                keyword = ''.join('{}{}'.format(first, second))
                # print('class key:', type(keyword), keyword)
                return keyword
        except AttributeError as error:
            print(error)
            print(section.dt.code)
            return False

    def section_header(section):
        ''' [ Header ] sections 
        - Feed (if exists) relative URLs to transform_relative_links()
        - Format html to markdown,
        '''
        if section.a is not None:
            internal_link = transform_relative_links(section.a['href'])
            section.a['href'] = internal_link
            # p.pprint(header_link.__dict__)
            url = section.a['href']
        else:
            url = None
        # < Hack > copy untouched section.dd 1st since we're destroying all 
        # spans & still need to manipulate them in body (section.dd) later
        store_dd = cp.copy(section.dd)
        for span in section.find_all('span'):
            span.unwrap()
        section.dd = store_dd   # put copy back
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
            # print('content section.dt:', content)
            transform_header.append(str(content))
        # Add horizontal rule below header
        # Format header section, add opening link tag. 
        tmp_header = '{0}[{1}'.format( markdown_header('h4'),
                h.handle(''.join(transform_header).strip()),
                )
        # remove double markdown link tag
        newtmp = tmp_header.replace(".``", ".")
        # string is immutable
        header = '{0}{1}'.format(newtmp.replace('[¶', ''), '-----\n')
        return header, url

    def section_body(section):
        ''' [ Body ] section 
        - Format the definition in Header
        - Convert internal & relative url links to absolute paths
        '''
        for link in section.dd.select('a[href]'):
            if link is not None:
                transform_link = transform_relative_links(link.attrs['href'])
                link.attrs['href'] = transform_link
        transform_body =[]
        for content in section.dd.contents:
            transform_body.append(str(content))
        body = str(h.handle(''.join(transform_body))).strip()
        return body

    def section_footer(section):
        ''' [ Footer ]
        - Include infos in docbots replies
        '''
        footer = None
        return footer

    """ Extract data from page """
    for section in _sections:
        if section_keyword(section):
            keyword = section_keyword(section)
            # print('got keyword:', keyword)
            header, url = section_header(section)
            # print('got header: {}got url: {}'.format(header, url))
            body = section_body(section)
            # print('got body:', body)
            footer = section_footer(section)
            # print('got footer:', footer, '\n')
            ''' Store all the data '''
            keyword_dict = { 
                'version': DOC_VERSION,
                'version_full': DOC_LONGVERSION,
                'version_micro': version_micro,
                'topic': DOC_TOPIC,
                'section': DOC_SECTION,
                'keyword': keyword,
                'url' : url,
                'header': header, 
                'body': body, 
                'footer': footer,
            }
            # datadump[keyword] = keyword_dict.copy() # faster than update()
            # print(keyword_dict)
            db_insert(table=db_table, 
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
                    )

""" Start """

''' LOCAL TEST CONFIGS '''
path = os.path.expanduser('~/Google Drive/docs/python-3.5.2_docs/library/')
# page = 'datetime.html'
# fullpath = os.path.join(os.path.expanduser(path), page)
# create_definitions(fullpath)

for root, dirs, filenames in os.walk(path):
    for fname in filenames:
        fullpath = os.path.join(root, fname)
        create_definitions(fullpath)

# descriptions = OrderedDict()
