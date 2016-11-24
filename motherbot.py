#!/usr/bin/env python
""""
[MotherBot] Syntax/docbot by /u/num8lock
Desc:       Model (logic module)
version:    v.0.2
git:   

"""
import os
import re
from datetime import date, datetime
import logging, logging.config
import ast
import copy as cp                       # to copy section
# import simplejson as json             # json store for sending data, new idea
from bs4 import BeautifulSoup as BS
import html2text
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from docdb import Library

log = logging.getLogger(__name__)
# load logging config in env variable
logging.config.dictConfig(ast.literal_eval(os.getenv('LOG_CFG')))

engine = create_engine('sqlite:///docbot.db', echo=True)
Session = sessionmaker(bind=engine)
session = Session()

''' LOCAL TEST CONFIGS '''
path = os.path.expanduser('~/Google Drive/docs/python-2.7.12_docs/library/')
# page = 'datetime.html'
# fullpath = os.path.join(os.path.expanduser(path), page)

def db_insert(table=None, version_id=None, version_major=None, 
    version_minor=None, version_micro=None, topic=None, section=None, 
    keyword=None, url=None, header=None, body=None, footer=None):
    pass
    # Create objects
    # if table == 'Library':


def build_definitions(fullpath):
    """ This is the main function to initialize the definitions data 
    Arguments: ==> TODO
        URL path
        datastore: database URL
        function name and query (optional for scraping new docs) 

    Process: start by getting the doc file
        - get the chuncks of sections of definition
        - process markup conversion on each of section into parts, 
        - keyword : exact syntax
        - header: function syntax & arguments
        - body: function definition
        - gather metadata into a dict: section link, h1 header
        - join all parts to a single section & store to database
    """
    # Initialize data from html source
    with open(fullpath, 'r', encoding='utf-8') as doc:
        _doc = BS(doc, 'lxml')
    datadump        = {}
    h               = html2text.HTML2Text()
    h.ignore_links  = False
    _sections       = _doc.find_all('dl')
    #   in <ul class="this-page-menu"> <...>
    #       <li><a href="../_sources/library/functions.txt"
    _src            = _doc.body.find(attrs={'class':'this-page-menu'})     
    _var_opt        = ''.join(_doc.head.script.contents)

    ''' [ Metadata ] for naming & hyperlinks
    - Get Python version from the html page header, set by javascript in 
      var DOCUMENTATIONS_OPTIONS
    - Get other info from url included to use for metadata, db & other variables
    '''
    _version        = re.search(r'VERSION.*\'([\d\.]+)\'', _var_opt)
    _suffix         = re.search(r'SUFFIX.*\'(\.\w+)\'', _var_opt)
    _part           = re.search(r'\.\./_sources/([\w]+)/([\w.]+)\.*', str(_src))
    # Initialize metadata variables
    DOC_ROOT        = 'https://docs.python.org'
    DOC_LONGVERSION =_version.group(1)  # i.e. 3.5.2
    DOC_VERSION     = DOC_LONGVERSION[0]    # i.e. 3
    DOC_TOPIC       = _part.group(1)          # i.e. library, references, etc
    DOC_SECTION     = os.path.splitext(_part.group(2))[0]  # i.e, functions, etc
    DOC_SUFFIX      = _suffix.group(1)
    DOC_VER_URL     = '{}/{}/'.format(DOC_ROOT, DOC_VERSION)
    DOC_SECTION_URL = '{}/{}/{}/'.format(DOC_ROOT, DOC_VERSION, DOC_TOPIC)
    DOC_FULL_URL = '{}/{}/{}/{}{}'.format(
                    DOC_ROOT, DOC_VERSION, DOC_TOPIC, DOC_SECTION, DOC_SUFFIX)
    if _part.group(1) == (DOC_ROOT or fullpath) and DOC_SECTION == 'glossary':
        DOC_TOPIC = 'glossary'

    ''' Set database variables, TODO for analytic & logging purposes
    See DocBot_Schema.sql 
    '''
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
                    ''' This match.span example basically just for reminder '''
                    #   debug(['<re matched group 3> : {} : {}{}'
                    #     .format(match.span(3), DOC_VER_URL, strings])
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
            log.error('URL cannot be replace with regex: {}'.format(exception), 
                exc_info=True)
            return False

    def markdown_header(arg):
        """ HTML to Markdown headers """
        header = {'h1': '# ', 'h2': '## ', 'h3': '### ', 'h4': '#### ', 
                    'h5': '##### ', 'h6': '###### '}
        return header[arg]

    def create_keyword(section):
        ''' [ Keywords ] 
        - Evaluate if section contains valid definition & extract the strings
        '''
        dt_parent = section.dt.parent
        keyword = ''
        while 'id' in section.dt.attrs:
            keyword = section.dt.attrs['id']
            # log.debug('>>> id key: {0}'.format(str(keyword)))
            return keyword
        try:
            if section.dt.code.next_sibling is not None:
                # log.debug('Looking in code css class')
                first = section.dt.code.text
                second = section.dt.code.next_sibling.string
                keyword = ''.join('{}{}'.format(first, second))
                return keyword
        except AttributeError as error:
            log.error('[ Keywords error]: {}'.format(error))
            log.warn("Skipping: can't find keyword in {}".format(section.dt.code))
            return False

    def create_header(section):
        ''' [ Header ] sections 
        - Feed (if exists) relative URLs to transform_relative_links()
        - Format html to markdown,
        '''
        if section.a is not None:
            internal_link = transform_relative_links(section.a['href'])
            section.a['href'] = internal_link
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
        # < Hack > around BS because making it output simple strings is like 
        # getting your money back from asshole you misjudged a long time ago
        transform_header = []
        for content in section.dt.contents:
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

    def create_body(section):
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

    def create_footer(section):
        ''' [ Footer ]
        - Include infos in docbots replies
        '''
        # readme_link = link
        # sub_docbot = sub
        # '\n\n`>>>` [README]({0}) |  `>>>` [/r/DocBot/]({1}'.format(
            # readme_link, sub_docbot)
        footer = None
        return footer

    ''' Extract data from page '''
    for section in _sections:
        if create_keyword(section):
            keyword = create_keyword(section)
            header, url = create_header(section)
            body = create_body(section)
            footer = create_footer(section)

            ''' Store all the data
            Arguments:
                table:          Database table name
                version_id:     Int, main variable for user <version> query
                version_major:  Int(major).x.x, i.e. 3.5.2, 2.7.12
                version_minor:  x.int(minor).x
                version_micro:  x.x.int(micro)
                topic:          Library (Python Doc **Section**)
                section:        Python doc page name, based on module name
                keyword:        Main variable for user <syntax> query
                url:            Permalink to Python doc syntax definition 
                header:         Syntax & argument part
                body:           Definition part
                footer:         Related document URLs & docbot information links
            '''
            doc = Library( 
                    version_id, version_major, version_minor, version_micro, 
                    DOC_TOPIC, DOC_SECTION, keyword, url, header, body, footer)
            log.info('Adding to database: {}'.format(doc))
            # is this safe?
            session.add(doc)
            session.flush()
    # commit the record the database
    session.commit()


for root, dirs, filenames in os.walk(path):
    for fname in filenames:
        fullpath = os.path.join(root, fname)
        log.info('Start importing definitions', exc_info=True)
        build_definitions(fullpath)

