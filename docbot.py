#!/usr/bin/env python
""""
[SyntaxBot] Reddit Python docbot by /u/num8lock
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
"""
import os
import re
import time
from datetime import datetime
import logging
import logging.config
import praw
import ast
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

''' CONFIGS '''
# Retrieve (Heroku) env private variables
ua = useragent = 'Python Syntax help bot for reddit v.0.1 (by /u/num8lock)'
appid = os.getenv('syntaxbot_app_id')
secret = os.getenv('syntaxbot_app_secret')
botlogin = os.getenv('syntaxbot_username')
password = os.getenv('syntaxbot_password')
# Reddit related variables
botcommand = 'SyntaxBot!'
subreddit = 'bottest'

# regex pattern for capturing user commands. Need to have everything 
# captured between the identifiers
pattern = re.compile(r"""(?P<bot>Doc!|DocBot!|SyntaxBot!)\s
    (?P<command>find|lookup|search|get)\s
    (?P<keywords>['"]{3}(.*)['"]{3})""", re.X)

def log_as_replied(comment):
    # check_bot_comments()
    pass

def check_replied(comment):
    """check if comment is already listed as replied in database"""
    replied_result = session.query(RedditActivity).filter(replied).all()
    for comment_id in replied_result:
        if comment_id == comment.id:
            return comment_id.replied
        else return False
    # return replied
    
def check_mentions():
    """Bots can and should monitor https://www.reddit.com/message/mentions.json 
    rather than polling/scraping every comment, whenever possible. 
    You can also monitor /api/v1/me and check the has_mail attribute to see if 
    you need to look up mentions.json"""
    # check_replied(mentions)
    pass

def check_pm():
    log.info('Checking PMs...')
    # check_replied(pm)
    pass

def parse(comment):
    """Process & log replied comment
    # get docbot replied posts firsts
    replied = comment.id
    replied_datetime = datetime.utcfromtimestamp(comment.created_utc)
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
        replied_list))
    """
    log.info('[Parsing]: comment id: {}, author: {}, query: {}'.format(
                comment.id, comment.author, comment.body))
    matches = re.search(pattern, comment.body)
    log.debug('Comment:\n{}\n{}\n{}\n{}\nMatch? {}\n'.format(
            '-'*80, comment.body, comment.__dict__, '-'*80, matches.group(4))
    )
    query = matches.group(4)
    log.debug(type(query))
    # if not matches:
    #     log.error('Error: cannot find query in comment. Check again?')   
    #     raise exception

def reply(comment):
    log.info('Replying...{}'.format(comment.__dict__))
    # double check to make sure current comment is not replied as there's a 
    # slight chance logging not finished when comment was found in search_result
    checked = check_replied(comment)
    if checked:
        log.debug('Already replied {} at {}. Skipping.'.format(
                [comment.id, comment.author], checked))
    query = parse_query(comment)
    # reply_query = get_formatted(query)
    # comment.reply(reply_query)
    # log_as_replied(comment)
    pass
    

def search(subreddit, limit):
    ''' Thanks u/w1282 for reminding what function in programming function means
        # * concerned with finding queries to the bot
        # * concerned with validating that it hasn't already been responded to
        # * concerned with gathering the proper information related to the query
        # * concerned with formatting the response
        # * concerned with posting the response

        # response = lookup_response(parsed_query)
        # formatted_response = format_response(response)
        # post_response(query, formatted_response)
    '''
    search_result = r.subreddit(subreddit).search(
                                '{0}'.format(keyword), time_filter='month')
    log.debug('Search result: {}'.format(search_result.__dict__))
    if search_result is None:
        log.info('No matching result.')
        return None
    for thread in search_result:
        ''' get OP thread / submission to iterate comment/replies '''
        log.debug('Iterating threads in search result : {}'.format(thread))
        # iterate every comments and their replies
        submission = r.submission(id=thread)
        submission.comments.replace_more(limit=0)
        for comment in submission.comments.list(): 
            # to make it non lazy >>> log.info(vars(comment))
            # docs../getting_started.html#get-available-attributes-of-an-object
            if comment.author == botlogin:
            # skip the replied comment & non-query comment
                continue
            log.debug('Processing comment tree: {} [{}]: {}'
                .format(comment, comment.author, submission.comments.list()))
            reply(comment)
            # log(comment.__dict__)

def whatsub_doc(subreddit, keyword):
    limit = 10
    search(subreddit, keyword, limit)
    check_pm()
    check_mentions()

def login():
    ''' praw4 only needs the first 3 for read-only mode '''
    log.info('Logging started')
    r = praw.Reddit(user_agent=ua, client_id=appid, client_secret=secret, 
        username=botlogin,
        password=password
        )
    ''' log connection '''
    log.info('Connected. Starting bot activity')
    return r

if __name__ == '__main__':
    log = logging.getLogger(__name__)
    logging.config.dictConfig(ast.literal_eval(os.getenv('LOG_CFG')))
    engine = create_engine('sqlite:///docbot.db', echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    ''' capture exceptions '''
    try:
        r = login()
        whatsub_doc(subreddit, botcommand)
    except ConnectionError as no_connection:
        log.error(no_connection, exc_info=True)
        time.sleep(100)
        log.info('Reconnecting in 10secs...')
        r = login()
        whatsub_doc(subreddit, botcommand)
