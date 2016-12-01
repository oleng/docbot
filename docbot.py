#!/usr/bin/env python
""""
[SyntaxBot] Python documentation bot for Reddit by /u/num8lock
Desc:       reddit module
version:    v.0.2
git:        
Notes:      praw4 (see requirements.txt)
            [Heroku] uses env variables for storing OAuth secret key and
            reddit account username/password
Acknowledgment:
            Codes based on many reddit bot creators /u/redditdev
            and helps from /r/learnpython.
            Thanks to:
            - u/w1282 for reminding what function in programming function means
            - u/bboe for authoring praw and making it easier to use reddit API
"""
import os
import re
import time
from datetime import datetime
import logging, logging.config
import praw
import ast
from sqlalchemy import create_engine, exists
from sqlalchemy.orm import sessionmaker
from docdb import Library as libdb 
from docdb import RedditActivity as reddb

''' CONFIGS '''
# Retrieve (Heroku) env private variables
ua = useragent  = 'Python Syntax help bot for reddit v.0.1 (by /u/num8lock)'
appid           = os.getenv('syntaxbot_app_id')
secret          = os.getenv('syntaxbot_app_secret')
botlogin        = os.getenv('syntaxbot_username')
passwd          = os.getenv('syntaxbot_password')
# Reddit related variables
botcommand      = 'SyntaxBot!'
sub_name        = 'bottest'

version3        = 352
version2        = 2712
default_version = version3
# regex pattern for capturing user commands. Need to have everything 
# captured between the identifiers
pattern = re.compile(r"""
    (?P<bot>Doc|DocBot|SyntaxBot[!\s])
    (?P<command>([-]?)|(find|get|lookup|search)|\s)
    (?P<query>['`\"\(-]?.*\b|$)""", re.I | re.X)
non_syntax = re.compile(r'''[\(\)\{\}\?!`\'\";\\\|+,:\s]''')


def mark_as_replied(comment, reply):
    """http://stackoverflow.com/a/1830499/6882768
    # get docbot replied posts firsts
     = comment.id
    query_datetime = datetime.utcfromtimestamp(comment.created_utc)
    # got this from (vars(submission.comments))
    _post = submission.comments._comments_by_id[comment.parent_id]
    comment_id = _post.id
    username = _post.author.__dict__['name']
    query_datetime = datetime.utcfromtimestamp(_post.created_utc)
    # keyword
    _q_re = re.search(pattern, _post.body)
    query_keyword = ''.join(str(_q_re.group(4))).replace('\(\)', '')
    permalink = 'https//reddit.com/r/{0}/comments/{1}'.format(
                sub_name, comment_id)
    replied_list = {
            'comment_id' : comment_id, 
            'username': username, 
            'query_keyword': query_keyword,
            'query_version': '',
            'query_topic': '',
            'query_datetime': query_datetime,
            'permalink': permalink,
            'replied': replied,
            'replied_datetime': replied_datetime
            }
    log.debug('Replied to: {}: {} \n{}'.format(vars(_post.author), 
        datetime.utcfromtimestamp(_post.created_utc), 
        replied_list))"""
    ''' double check own profile for replies listed '''
    # check_profile(comment)
    pass


def valid_query(comment):
    """Searching valid formatted command in comment, if found, strip non query 
    parts in comment.body. Return False or full query string(s)"""
    find_query = re.search(pattern, comment.body)
    if not find_query:
        log.debug('Error: cannot find query in %s', comment)
        log.debug('\n{}\n>> {}\n>> {}\n{}'.format(
                '-'*80, comment.body, comment.__dict__, '-'*80)
        )
        return False
    _query = '{0}{1}'.format( find_query.group('command'),
                              find_query.group('query') )
    log.debug('Valid query: %s', find_query.groupdict())
    return _query


def check_replied(comment):
    """check if comment is already listed as replied in database"""
    # change column replied to replied_id for naming comprehension
    comment_result = session.query(reddb.comment_id, reddb.replied).filter(
                                    reddb.comment_id == comment.id).first()
    if comment_result:
        log.debug('Replied: [%s] %s', comment_result[0], comment_result[1])
        return True
    else: return False

    
def check_mentions():
    """Bots can and should monitor https://www.reddit.com/message/mentions.json 
    rather than polling/scraping every comment, whenever possible. 
    You can also monitor /api/v1/me and check the has_mail attribute to see if 
    you need to look up mentions.json"""
    log.info('Checking /u/SyntaxBot mentions...')
    # check_replied(mentions)
    pass


def check_pm():
    """ Check Private Messages for queries """
    log.info('Checking PMs...')
    # check_replied(pm)
    pass


def parse(query):
    """Get query definitions from libdb database"""
    # see docs/library/functions.html?highlight=filter#filter
    list_query = [*filter(None, re.split(non_syntax, query.strip()))]
    log.debug('Start parsing: %s', list_query)
    _d = _definition = {'version': 'version_id', 'search': 'keyword', 
                        'module': 'module'}
    query_types = {
        'v': _d['version'], 'version': _d['version'], 
        'm': _d['module'], 'module': _d['module'], 
        'f': _d['search'], 'find': _d['search'], 's': _d['search'], 
        'search': _d['search'], 'get': _d['search'], 'lookup': _d['search']
        }
    queries = {}
    for i, arg in enumerate(list_query):
        log.debug('parsing: i: %s, %s', i, arg)
        qkeyword = list_query[i + 1]
        queries[query_types[arg.strip('-')]] = qkeyword
        log.debug('parsing: appended arg to queries: {%s: %s}', 
            query_types[arg.strip('-')], qkeyword
        )
        log.debug('parsing: pop next arg: %s', list_query[i + 1])
        list_query.pop(i + 1)
    log.debug('parsing: queries dict result: %s', queries)
    # http://stackoverflow.com/a/14516917/6882768
    try:
        log.debug('parsing: Set up version_id in: %s', queries['version_id'])
        queries['version_id'] = queries['version_id'].replace('.', '')
        if queries['version_id'].replace('.', '').isdigit() \
           and queries['version_id'].startswith('2', 0, 1):
                queries['version_id'] = version2
        else:
            queries['version_id'] = default_version
        log.debug('parsing: version_id: stripped? %s', queries['version_id'])
    except KeyError as err:
        log.error('parsing: No version defined in %s, %s missing', queries, err)
        queries['version_id'] = default_version
    log.info("Parsed: %s", queries)

    # DB queries
    main_keyword = queries['keyword']
    main_ver = queries['version_id']
    option = queries['keyword'].rsplit('.', maxsplit=1)[0]
    # Data needed to process a reply:
    columns = [ libdb.id, libdb.version_id, libdb.module, libdb.keytype, 
                libdb.keyclass, libdb.keyword, libdb.url, libdb.header, 
                libdb.body, libdb.footer ]

    log.info('> Query check: Version: `%s`. Keyword: `%s`, Module (opt): `%s`', 
                main_ver, main_keyword, option)
    # check if keyword exists, from sqlalchemy creator
    # http://techspot.zzzeek.org/2008/09/09/selecting-booleans/
    main_check = session.query(exists().where(
                libdb.keyword.contains(main_keyword)).where(
                libdb.version_id == main_ver)).scalar()
    opt_check = session.query(exists().where(libdb.module == option)
                .where(libdb.version_id == main_ver)).scalar()
    log.debug('> Exists? main_query: %s. opt_query: %s.', main_check, opt_check)
    
    if main_check:
        # group by module hopefully = better search (motherbot:build_definitions)
        main_query = session.query(*columns).filter(
                (libdb.keyword.contains(main_keyword)) & 
                (libdb.version_id == main_ver)
                ).group_by(libdb.module).order_by(libdb.id).first()
        log.debug('Library returns (main_query): id: %s, vers: %s, keyword: %s', 
                    main_query.id, main_query.version_id, main_query.keyword)
        return main_query, 'main'
    elif opt_check:
        # idkwhy exact word module w/ grouping keyword resulted to first keyword 
        log.info('opt_query: Query Library.module instead of Library.keyword')
        opt_query = session.query(*columns).filter(
                (libdb.module == option) & (libdb.version_id == main_ver)
                ).group_by(libdb.keyword).order_by(libdb.id).first()
        log.debug('Library returns (opt_query): id: %s, vers: %s, module: %s',
                    opt_query.id, opt_query.version_id, opt_query.module)
        return opt_query, 'option'
    else:
        log.error('Nothing found for query %s', query)
        return None


def format_response(data, comment):
    """Format bot reply to user query"""
    permalink = 'https://www.reddit.com/r/{0}/comments/{1}/comment/{2}'.format(
                sub_name, comment.link_id.split('_')[1], comment.id)
    if data is None:
        # for `not found` reply
        query = valid_query(comment)
        botreply = """Sorry, {0}, I can't seem to find what you're asking here  
            [`{1}`]({2}). Maybe a typo?  \nYou can PM me to try 
            another request, though.  \n{3}""".format(
            comment.author, query, permalink, data.footer)
    else:
        reply_data = data[0]
        reply_type = data[1]
        botreply = """{0} \n {1} \n {2} \n {3}""".format(reply_type, permalink,
            reply_data.header, reply_data.body)
    return botreply


def reply(comment):
    """Reply user comment"""
    # double check? to make sure current comment is not replied as there's a 
    # slight chance marked_as_replied not yet finished
    # checked = check_replied(comment)
    # if checked:
    #     log.debug('Ignoring, %s already replied at %s', comment.id,  checked)
    #     return
    ##
    response_data = parse(valid_query(comment))
    log.info('Replying...{}'.format( 
            { comment.id: [ datetime.utcfromtimestamp(comment.created_utc), 
            comment.author.name, response_data[0].id, response_data[1] ] } ) )
    # pass comment too for logging purpose
    bot_response = format_response(response_data, comment)
    log.debug('Reply message: %s', bot_response)
    # comment.reply(bot_response)
    # mark_as_replied(comment)
    pass


def search(subreddit, keyword, limit):
    ''' # * concerned with finding queries to the bot
        # * concerned with validating that it hasn't already been responded to
        # * concerned with gathering the proper information related to the query
        # * concerned with formatting the response
        # * concerned with posting the response
    '''
    search_result = r.subreddit(subreddit).search('{0}'.format(
                    keyword), time_filter='month')
    log.debug('Search result: {}'.format(search_result.__dict__))
    if search_result is None:
        log.info('No matching result.')
        return None
    for thread in search_result:
        ''' get OP thread / submission to iterate comment/replies '''
        log.debug('Iterating threads in search result : %s', thread)
        # iterate every comments and their replies
        submission = r.submission(id=thread)
        submission.comments.replace_more(limit=0)
        log.debug('Processing comment tree: {} [{}]: {}'.format(
            submission, submission.author, submission.comments.list()
        ))
        for comment in submission.comments.list(): 
            # skip own & replied comment
            if comment.author == botlogin:
                log.info('Skipping own comment: %s', comment)
                continue
            elif check_replied(comment):
                log.info('Skipping comment %s: replied', comment)
                continue
            # skip non-query comment
            elif not valid_query(comment):
                log.info('Skipping comment %s: no query found', comment)
                continue
            else:
                reply(comment)


def whatsub_doc(subreddit, keyword):
    """Main bot activities & limit rate requests to oauth.reddit.com"""
    limit = 10
    search(subreddit, keyword, limit)
    check_pm()
    check_mentions()


def login():
    """praw4 OAuth2 login procedure"""
    ''' praw4 only needs the first 3 for read-only mode '''
    log.info('Logging started')
    r = praw.Reddit(user_agent=ua, client_id=appid, client_secret=secret, 
        username=botlogin,
        password=passwd
        )
    ''' log connection '''
    log.info('Connected. Starting bot activity')
    return r


if __name__ == '__main__':
    log = logging.getLogger(__name__)
    logging.config.dictConfig(ast.literal_eval(os.getenv('LOG_CFG')))
    engine = create_engine('sqlite:///docbot.db', echo=True)
    Session = sessionmaker(bind=engine)
    session = Session()
    ''' capture exceptions '''
    try:
        r = login()
        whatsub_doc(sub_name, botcommand)
    except ConnectionError as no_connection:
        log.error(no_connection, exc_info=True)
        time.sleep(100)
        log.info('Reconnecting in 10secs...')
        r = login()
        whatsub_doc(sub_name, botcommand)
