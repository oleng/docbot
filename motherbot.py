#!/usr/bin/env python
""""
[MotherBot] Syntax/docbot by /u/num8lock
Desc:       Model (logic module)
version:    v.0.3
git:   

CHANGES:    
2016/12/02  Moved from SQLite3 to PostgreSQL, only version 3 data due to number 
            of columns limitation on free tier Heroku
"""
import os
import re
import ast
import logging, logging.config
from datetime import date, datetime
import copy as cp                       # to copy section
from random import randrange
from bs4 import BeautifulSoup as BS
import html2text
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from docdb import Library

log = logging.getLogger(__name__)
# load logging config from env variable
logging.config.dictConfig(ast.literal_eval(os.getenv('LOG_CFG')))

''' LOCAL TEST CONFIGS '''
docvers = '3.5.2'
path = os.path.expanduser('~/Google Drive/docs/python-docs/{}/library/'.format(
                                                                    docvers))
    
def json_builder(data, path):
    """Create JSON object and file to store the definitions
    Failed to make it work for now"""
    # try: 
    #     import simplejson as json
    # except ImportError as err:
    #     import json
        # log.error('Cannot import simplejson, use builtin json module instead.')
    _module, _type, _class = data[0]
    _keyword = data[1]
    _response_data = data[2]
    _data = { 'meta': {'module': _module, 'keytype': _type, 'keyclass': _class},
            'keywords': _keyword, 
            'data': _response_data,
            }
    serialized = json.dumps(_data, 
                sort_keys=True, ensure_ascii=False).encode('utf-8')
    # # development: save json files
    # filepath = './json/{0}.{1}.json'.format(_keyword[0], docvers)
    # with open(filepath, 'wb') as jsonfile:
    #     jsonfile.write(serialized)
    log.info('%s', serialized)
    return serialized


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
    #   in... <ul class="this-page-menu"> <...>
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
    DOC_LONGVERSION = _version.group(1)  # i.e. 3.5.2
    DOC_VERSION     = DOC_LONGVERSION[0]    # i.e. 3
    DOC_TOPIC       = _part.group(1)          # i.e. library, references, etc
    DOC_MODULE      = os.path.splitext(_part.group(2))[0]  # i.e, functions, etc
    DOC_SUFFIX      = _suffix.group(1)
    DOC_VER_URL     = '{}/{}/'.format(DOC_ROOT, DOC_VERSION)
    DOC_MODULE_URL  = '{}/{}/{}/'.format(DOC_ROOT, DOC_VERSION, DOC_TOPIC)
    DOC_FULL_URL    = '{}/{}/{}/{}{}'.format(DOC_ROOT, DOC_VERSION, DOC_TOPIC, 
                                            DOC_MODULE, DOC_SUFFIX)
    if _part.group(1) == (DOC_ROOT or fullpath) and DOC_MODULE == 'glossary':
        DOC_TOPIC = 'glossary'

    ''' Set database variables, TODO for analytic & logging purposes
    See DocBot_Schema.sql 
    '''
    db_table        = DOC_TOPIC.capitalize()  
    version_id      = ''.join(DOC_LONGVERSION.split('.'))
    major           = version_id[0]
    minor           = version_id[1]
    micro           = version_id[2:]


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
                    return r'{}{}'.format(DOC_MODULE_URL, match.group(2))
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
        except re.error as err:
            log.error('URL cannot be replace with regex: {}'.format(err), 
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
                log.debug('creating... [id]: (%s) %s', keytype, _keyword)
            elif section.dt.find(class_='descname'):
                # for readability
                keytype = section['class'][0]
                if section.dt.find(class_='descclassname') is None: 
                    log.debug('`Descclassname` not found')
                    _keyword = section.dt.find(class_='descname').string
                    log.debug('creating... [css] _keyword: %s', _keyword)

                elif section.dt.find(class_='descclassname') is not None:
                    log.debug('Found css `descclassname`')
                    descclass = section.dt.find(class_='descclassname').string
                    log.debug('Found css `descname`')
                    descname = section.dt.find(class_='descname').string
                    _keyword = '{}{}'.format(descclass, descname)
                    log.debug('creating... [css] _keyword: %s', _keyword)
            '''separate class from methods & functions based on the length of 
            syntax we have so far. note: this is not in above loop 
            `descclass name not found` because [id]'''
            if len(_keyword.split('.')) == 1:
                log.debug('creating... One word syntax %s', _keyword)
                keyclass = keytype
                return keytype, keyclass, [_keyword]
            elif len(_keyword.split('.')) == 2:
                log.debug('creating... Two word syntax %s', _keyword)
                keyclass = _keyword.split('.')[0]
                return keytype, keyclass, [_keyword]
            elif len(_keyword.split('.')) > 2:
                log.debug('creating... More than two word syntax %s', _keyword)
                _keys = _keyword.split('.', maxsplit=1)
                keyclass = _keys[0]
                splitkeys = _keys[1].split('.')
                keyword = []
                for i, val in enumerate(splitkeys):
                    if i == len(splitkeys) - 1:
                        break
                    else:
                        keyword.append('.'.join(splitkeys[i : ]))
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


    def create_footer(keyword):
        """ [ Footer ] Include infos in docbots replies"""
        length = len(keyword) - 1 if len(keyword) > 1 else 1
        randsyn = keyword[randrange(0, length)]
        msg_template = 'SyntaxBot --find {0} --version 3'.format(randsyn)
        # stolen from RemindMeBot 
        pm_link = \
        'https://np.reddit.com/message/compose/?to={0}&subject={1}&message={2}' \
        ''.format('SyntaxBot', randsyn, msg_template)
        readme_link = 'https://www.reddit.com/r/SyntaxBot/'        
        footer      = '-----\n`>>>` [README]({0}) | `>>>` ' \
                    '[Try get it from PM!]({1})'.format(readme_link, pm_link)

        log.debug('Creating footer')
        return footer


    ''' Extract data from page '''
    for section in _sections:
        if 'docutils' in section['class']:
            log.warn('class docutils, Skipping, not a definition. %s', section)
            continue
        elif valid(section):
            keytype, keyclass, keyword = create_keywords(section)
            header, url = create_header(section)
            body = create_body(section)
            footer = create_footer(keyword)
            data = '{0} \n {1} \n {2}'.format(header, body, footer)
            # unpack keyword list
            keywords = ', '.join(keyword)
            log.info('(%s) keytype: %s, keyclass: %s, keyword: %s', 
                        version_id, keytype, keyclass, keyword)
            log.info('`%s` section done.\n', 
                        section.dt.find(class_='descname').string)
            ''' Store all the data
            Arguments:
                Database columns:
                table:          Database table name
                version_id:     Int, main variable for user <version> query
                major:          Int(major).x.x, i.e. 3.5.2, 2.7.12
                minor:          x.int(minor).x
                micro:          x.x.int(micro)
                topic:          Library (Python Doc **Section**)
                module:         Python doc page name, based on module name
                keytype:        Class, method, function or attribute
                keywords:       Strings, main variable for user <syntax> query        
                header:         Syntax & argument part
                body:           Definition part
                footer:         Related document URLs & docbot information 
                                links
                url:            Permalink to Python doc syntax definition 
            '''
            doc = Library(
                    version_id=version_id, major=major, 
                    minor=minor, micro=micro, 
                    topic=DOC_TOPIC, module=DOC_MODULE, keytype=keytype, 
                    keyclass=keyclass, keywords=keywords, header=header, 
                    body=body, footer=footer, url=url
                    )
            # commit only when all definitions added to session
            session.add(doc)
            session.flush()
    # commit the record the database and close connection
    session.commit()

'''
'''
db_config = os.getenv('DATABASE_URL')
engine = create_engine(db_config, echo=True, isolation_level="READ COMMITTED")
Session = sessionmaker(bind=engine)
session = Session() 

for root, dirs, filenames in os.walk(path):
    for fname in filenames:
        fullpath = os.path.join(root, fname)
        log.info('Start importing definitions %s', fullpath , exc_info=True)
        build_definitions(fullpath)

# build_definitions(path)
session.close()
