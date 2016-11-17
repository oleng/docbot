#!/usr/bin/env python
""""
[MotherBot] Syntax/docbot by /u/num8lock
Desc:       Model (logic module)
version:    v.0.1
git:   

"""
import os
import re
import pprint as p
import copy as cp
from collections import OrderedDict
from bs4 import BeautifulSoup as BS
import html2text

''' LOCAL TEST CONFIGS '''
path = '~/Google Drive/docs/python-3.5.2_docs/library/'
page = 'functions.html'
fullpath = os.path.join(os.path.expanduser(path), page)
# descriptions = OrderedDict()

def create_definitions(fullpath, datastore=None, **kwargs):
    '''This is the main class to initialize the definitions data 
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
    ''' 
    def __init__():
        '''
        Get Python version from document page (set by js: 
        var DOCUMENTATIONS_OPTIONS) and use them for variables to include in 
        metadata
        '''
        datadump = []
        meta = {}
        h = html2text.HTML2Text()
        h.ignore_links = False
        with open(fullpath, 'r', encoding='utf-8') as doc:
            _doc = BS(doc, 'lxml')
        # datadump.append(sections)
        _sections = _doc.find_all('dl')
        _src = _doc.body.find(attrs={'class':'this-page-menu'})
        _var_opt = ''.join(_doc.head.script.contents)
        ''' [ Metadata ] for hyperlinks '''
        _version = re.search(r'VERSION.*\'([\d\.]+)\'', _var_opt)
        _suffix = re.search(r'SUFFIX.*\'(\.\w+)\'', _var_opt)
        _part = re.search(r'\.\./_sources/([\w]+)/([\w]+)\.*', str(_src))
        # Initialize variables for metadata
        DOC_ROOT = 'https://docs.python.org'
        DOC_LONGVERSION =_version.group(1)
        DOC_VERSION = DOC_LONGVERSION[0]
        DOC_SRC = _part.group(1)
        DOC_PAGE = _part.group(2)
        DOC_SUFFIX = _suffix.group(1)
        DOC_VER_URL = '{}/{}/'.format(DOC_ROOT, DOC_VERSION)
        DOC_PART_URL = '{}/{}/{}/'.format(DOC_ROOT, DOC_VERSION, DOC_SRC)
        DOC_FULL_URL = '{}/{}/{}/{}{}'.format(
                        DOC_ROOT, DOC_VERSION, DOC_SRC, DOC_PAGE, DOC_SUFFIX)

        meta['version'] = DOC_VERSION
        meta['version_full'] = DOC_LONGVERSION
        meta['doc_part'] = DOC_SRC
        if DOC_SRC == DOC_ROOT and DOC_PAGE == 'glossary':
            meta['doc_part'] = 'glossary'
        
        def internal_ref(arg):
            ''' Replace page internal references and relative urls '''
            try:
                def subpattern(match):
                    if match.group(1):
                        # print('<re matched group 1!> : {}{}'
                        #     .format(DOC_FULL_URL, match.group(1)))
                        return r'{}{}'.format(DOC_FULL_URL, match.group(1))
                    elif match.group(2):
                        # print('<re matched group 2!> : {}{}'
                        #     .format(DOC_PART_URL, match.group(2)))
                        return r'{}{}'.format(DOC_PART_URL, match.group(2))
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
            header = {'h1': '# ', 'h2': '## ', 'h3': '### ', 'h4': '#### ', 
                        'h5': '##### ', 'h6': '###### '}
            return header[arg]

        def markdown_note_changes(arg):
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
            """fix annoying trailing space in <em>class </em> to avoid
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
            ''' [ Keywords ] section    '''
            keyword = section.code.text
            
            ''' [ Title ] sections '''
            # start manipulate html elements: get the full html
            # replace relative URLs in href to absolute path using regex
            internal_link = internal_ref(section.a['href'])
            if internal_link is not False:
                section.a['href'] = internal_link
                # p.pprint(title_link.__dict__)
            section_link = section.a['href']
            # print('link:', section_link)
            # insert link for metadata
            meta['url'] = section_link
            # copy untouched section.dd first since we still want to 
            # manipulate span in section.dd later
            store_dd = cp.copy(section.dd)
            for span in section.find_all('span'):
                span.unwrap()
            section.dd = store_dd
            # Process title data
            title = section.dt
            # print('store:', title)
            # fix annoying trailing space in <em>class </em> to avoid 
            # incorrect markdown formatting
            # print('em:', section.dt.em)
            for em in section.dt.find_all('em', {'class': 'property'}):
                # print('strip:', em.string.replace_with('class'))
                next_txt = em.next_sibling.string
                # print('next:', em.next_sibling.string.replace_with(
                    # " `{}`".format(next_txt)))
                # unwrap the sibling to avoid double markup
                em.next_sibling.unwrap()
                # print('em:', em.__dict__)
            # print('em:', title.em)
            transform_title =[]
            for x in title.contents:
                # print('x:', x)
                transform_title.append(str(x))
            # Format title section
            title = '{0}{1}'.format(
                    markdown_header('h5'),
                    h.handle(''.join(transform_title).strip()),
                    # '\n'
                    )
            # print('title:', title.replace('¶', '^URL'))
            # print('tr: ', transform_title)
            # title[-1] = transform_link
            # print('section: ', section)
            ''' flatten Tag objects to strings '''
            # for i, val in enumerate(title):
            #     if type(val) != str:
            #         print('{}\nvalue: {}, i: {}'.format(title, val, i))
            # transform_title = h.handle(title.string).strip().replace("',", "")
            # convert title to markdown
            # transform_link = h.handle(title_link).replace('¶', '^&sect;')
            # print("".join(transform_title))
            # for c in title:
            #     print(''.join(str(c)))
            # for c in title_link:
                # title[-1:] = ''.join(str

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
            tmp = []
            for css in html_replacement:
                # ugly hack, didn't work
                for tag in section.dd.find_all(['div', 'span'], attrs={'class': css}):
                    if tag:
                        tag.unwrap()
                        # print(tag)

            body = section.dd
            transform_body =[]
            for x in body.contents:
                # print('x:', x)
                transform_body.append(str(x))
            body = h.handle(''.join(transform_body).strip())
            # internal_link = internal_ref(link.a['href'])
                
            # print('body: ::: ', body)

            footer = apply_footer(DOC_FULL_URL)
            datadump.append(
                {   'keyword': keyword, 
                    'title': title, 
                    'body': body, 
                    'footer': footer,
                    'metadata': meta    }
            )
        p.pprint(datadump)


    def apply_footer(url):
        pass

    __init__()


create_definitions(fullpath)

"""
        for desc in dl_tag:
                
                desc_keyword = desc.dt.code.get_text(strip=True)
                # first pass to replace html tags uncaught by html2text
                _replace_markup(desc.dt, ['code', 'em', 'span'])
                desc_title = h.handle(desc.dt.text)
                desc_content = desc.dd
                
                # desc_title = h.handle(desc.dt.prettify())
                # desc_content = h.handle(desc.dd.prettify())
                print('link: {}\ncontent: {}'.format(desc_title, desc_content))
                # store the result to datastore
                # log and stdout the result
                with open('description.txt', 'a', encoding='utf-8') as f:
                    # f.write('keyword: {0}\ntitle: {1}\ndefinition: {2}\n\n'
                    #     .format(desc_keyword, desc_title, desc_content)
                    #     )
                    f.write('{0}\n{1}\n'
                        .format(desc_title, desc_content)
                        )

    markdown_wrap = {

        # 'a': re.sub(
        #         r'(\"|\'#)',
        #         r'https://docs.python.org/%s/library/functions.html\1" % docversion[0]', 
        #         '\1'),
        'blockquote': ' > ', 'b': '**', 'code': '`', 'div': '', 
        'dt': '### ', 'em': '_', 'hr': '\n*****\n', 'p': '\n\n', 
        'pre': '    ', 'span': '', 
        }
    css_class_identifiers = {
        'headerlink': html_markdown['code'], 
        'internal': html_markdown['b'],
        'property': html_markdown['em'], 
        'versionadded': html_markdown['blockquote'], 
        'versionmodified': html_markdown['em'], 
        'admonition-title': html_markdown['blockquote']
        }
    escape_chars = { '*': '\*', '_': '\_' }

    def _replace_markup(soup, search_tags):
        for tag in soup.find_all(search_tags):
            # print('-----\nremoving tag {} in :\n {}\n-----'.format(tag.name, tag))
            if tag is not None and tag.name in html_markdown:
                # new_tag = html_markdown[tag.name]
                _markup = html_markdown[tag.name]
                if tag.name == 'dt' or 'a':
                    print('dt or a:', tag)
                    continue
                    # tag.replace_with(_markup)

                new_string = tag.string
                tag.replace_with(
                    '{0}{1}{0}'.format(_markup, new_string)
                    )
                # new_string = tag.string
                # del tag
                # print('name: {}, replaced with: {} for {}\n-----\n'.format(tag, new_string, html_markdown[tag.name]))
                # print('tag: {}\n-----\n'.format(tag))
        print(soup)
        return soup


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
