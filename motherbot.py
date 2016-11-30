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
# load logging config from env variable
logging.config.dictConfig(ast.literal_eval(os.getenv('LOG_CFG')))

engine = create_engine('sqlite:///docbot.db', echo=True)
Session = sessionmaker(bind=engine)
session = Session()

''' LOCAL TEST CONFIGS '''
path = os.path.expanduser('~/Google Drive/docs/python-2.7.12_docs/library/')


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
    major = version_id[0]
    minor = version_id[1]
    micro = version_id[2:]

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

    def valid(section):
        """[ Keywords ] Evaluate if section contains valid definition"""
        # log.debug(section)
        try:
            if 'id' in section.dt.attrs:
                return True
            elif section.dt.code.next_sibling is not None:
                return True
            else:
                log.warn('Skipping: can\'t find keyword in %s', section.dt.code)
                return False
        except AttributeError as error:
            log.error(error)
            return False

    def create_keywords(section):
        """ [ Keywords ] Extract definition type (class, method, etc) and 
        keyword strings"""
        # log.debug('Creating keyword')
        try:
            if 'id' in section.dt.attrs:
                keytype = section['class'][0]
                _keyword = section.dt['id']
                log.debug('[id]: (%s) %s', keytype, _keyword)
            # elif section.dt.code.next_sibling is not None or \
            elif section.dt.find(class_='descname'):
                # for readability
                keytype = section['class'][0]
                if section.dt.find(class_='descclassname') is None: 
                    log.debug('`Descclassname` not found')
                    _keyword = section.dt.find(class_='descname').string
                    log.debug('[css] _keyword: %s', _keyword)
                elif section.dt.find(class_='descclassname') is not None:
                    log.debug('Found css `descclassname`')
                    descclass = section.dt.find(class_='descclassname').string
                    log.debug('Found css `descname`')
                    descname = section.dt.find(class_='descname').string
                    _keyword = '{}{}'.format(descclass, descname)
                    log.debug('[css] _keyword: %s', _keyword)

            # separate the types based on the length of what we have so far
            # default when there's only a single syntax specified in doc
            if len(_keyword.split('.')) < 2:
                log.debug('One word syntax %s', _keyword)
                keyclass = keytype
                return keytype, keyclass, _keyword
            # everything else. 7 is too much, but there's a bug i think in this 
            # doc url that cause an exception error only 6: docs/3/library/
            # urllib.parse.html#urllib.parse.urllib.parse.SplitResult.geturl
            elif 7 > len(_keyword.split('.')) > 1:
                keyclass = _keyword.split('.')[0]
                keyword = _keyword
                for index, val in enumerate(_keyword.split('.')[1:]):
                    keyword += ', {}'.format(
                                    '.'.join(_keyword.split('.')[index + 1:])
                                    )
            log.debug('%s', keyword)
            return keytype, keyclass, keyword

        except AttributeError as error:
            log.error('Keywords error: %s', (error))
            log.warn("Skipping: can't find keyword in %s", section.dt.code)
            return False

    def create_header(section):
        """ [ Header ] Convert anchors/relative URLs to absolute paths if exists
        then convert html markups to markdown."""
        # log.debug('Creating header')
        if section.a is not None:
            internal_link = transform_relative_links(section.a['href'])
            section.a['href'] = internal_link
            url = section.a['href']
        else:
            log.warn('No internal anchors/links found %s', section.string)
            url = None
        # < Hack > copy untouched section.dd 1st since we're destroying all 
        # spans & still need to manipulate them in body (section.dd) later
        store_dd = cp.copy(section.dd)
        for span in section.find_all('span'):
            span.unwrap()
        # put copy back
        section.dd = store_dd   
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
        header = '{0}{1}'.format(newtmp.replace('[¶', ''), '-----')
        # log.info('Constructed %s', header)
        return header, url

    def create_body(section):
        """ [ Body ] Convert anchors/relative URLs to absolute paths if exists
        Format the definition in Header"""
        # log.debug('Creating body')
        for link in section.dd.select('a[href]'):
            if link is not None:
                transform_link = transform_relative_links(link.attrs['href'])
                link.attrs['href'] = transform_link
            else:
                log.debug('Link? %s', link)
        transform_body =[]
        for content in section.dd.contents:
            transform_body.append(str(content))
        body = str(h.handle(''.join(transform_body))).strip()
        # log.debug('Constructed body: %s', body)
        return body

    def create_footer(section):
        """ [ Footer ] Include infos in docbots replies"""
        # readme_link = link
        # sub_docbot = sub
        # '\n\n`>>>` [README]({0}) |  `>>>` [/r/DocBot/]({1}'.format(
            # readme_link, sub_docbot)
        # log.debug('Creating footer')
        footer = None
        return footer

    ''' Extract data from page '''
    for section in _sections:
        if 'docutils' in section['class']:
            log.warn('Skipping, not a syntax definition. %s', section)
            continue
        elif valid(section):
            keytype, keyclass, keyword = create_keywords(section)
            header, url = create_header(section)
            body = create_body(section)
            footer = create_footer(section)
            log.info('(%s) keytype: %s, keyclass: %s, keyword: %s', 
                        version_id, keytype, keyclass, keyword)
            log.info('`%s` section done.\n', 
                        section.dt.find(class_='descname').string)
            ''' Store all the data
            Arguments:
                table:          Database table name
                version_id:     Int, main variable for user <version> query
                major:          Int(major).x.x, i.e. 3.5.2, 2.7.12
                minor:          x.int(minor).x
                micro:          x.x.int(micro)
                topic:          Library (Python Doc **Section**)
                section:        Python doc page name, based on module name
                keytype:        Class, method, function or attribute
                keyword:        Main variable for user <syntax> query
                url:            Permalink to Python doc syntax definition 
                header:         Syntax & argument part
                body:           Definition part
                footer:         Related document URLs & docbot information links
            # 
            # '''
            doc = Library(
                    version_id=version_id, major=major, 
                    minor=minor, micro=micro, 
                    topic=DOC_TOPIC, module=DOC_SECTION, keytype=keytype, 
                    keyclass=keyclass, keyword=keyword, 
                    url=url, header=header, body=body, footer=footer,)
            # commit only when all definitions added to session
            session.add(doc)
            session.flush()
    # commit the record the database and close connection
    session.commit()

for root, dirs, filenames in os.walk(path):
    for fname in filenames:
        fullpath = os.path.join(root, fname)
        log.info('Start importing definitions %s', fullpath , exc_info=True)
        build_definitions(fullpath)

# build_definitions(path)
session.close()
