#!/usr/bin/env python
""""
[SyntaxBot] Reddit Python docbot by /u/num8lock
Desc:       reddit module
version:    v.0.1
git:        
Notes:      praw4 (see requirements.txt)
            [Heroku] uses env variables for storing OAuth secret key and
            reddit account username/password
Acknowledgment:
            Codes based on many reddit bot creators /u/redditdev
            and helps from /r/learnpython.

"""
# import motherbot
import os
import time
import re
import ast
from datetime import datetime
import praw
import pprint as pr

''' CONFIGS '''
# Retrieve (Heroku) env private variables
ua = useragent = 'Python Syntax help bot for reddit v.0.1 (by /u/num8lock)'
id = os.environ['syntaxbot_app_id']
secret = os.environ['syntaxbot_app_secret']
username = os.environ['syntaxbot_username']
password = os.environ['syntaxbot_password']
# Reddit related variables
botname = 'DocBot!'
subreddit = 'bottest'
# regex pattern for capturing user commands. Need to have everything 
# captured between the identifiers
pattern = re.compile(r'''
    (?P<bot>Doc!|DocBot!|SyntaxBot!) (?P<command>lookup|search) 
    (?P<keywords>[\'|\"]{3}(.*)[\'|\"]{3})''', re.IGNORECASE)
identifiers = '\"\''
# add logging. make it both logs to file.log & output to console stdouput
replied_list = ['d9x043o']

def login():
    ''' log connection '''
    print('Establishing connection...')
    ''' praw4 need only the first 3 for read-only mode '''
    r = praw.Reddit(user_agent=ua, client_id=id, client_secret=secret, 
        username=username,
        password=password
        )
    print('Connected. Starting bot activity')
    return r

def test_break():
    userinput = input("Just testing, ctrl+c to interrupt.")

def search_sub(subreddit, limit):
    r = login()
    search_result = r.subreddit(subreddit).search(
        '{0}'.format(botname), time_filter='week')
    print(search_result.__dict__)
    # test_break()

    for thread in result:
        ''' get OP thread / submission to iterate comment/replies '''
        submission = r.submission(id=thread)
        ''' check if already replied, reply if not '''
        # if thread not in replied_list:
        #     reply_op = get_doc(submission.selftext)
        #     submission.reply(reply_op)
        ''' log the thread submission '''
        # replied_list.append(submission.id, reply_op)
        # print(
        #     thread,
        #     submission.author,
        #     submission.created_utc,
        #     submission.title,
        #     submission.selftext,
        #     submission.num_comments,
        #     submission.permalink
        #     )
        # iterate every comments and their replies
        submission.comments.replace_more(limit=0)
        for comment in submission.comments.list(): 
            ''' skip the replied comment '''
            # if comment in replied_list: continue
            ''' log the comments '''
            matches = re.search(pattern, comment.body)
            ''' check unreplied comment for calls and if found process query '''
            if matches:
                ''' log starting point '''
                print(comment.id, comment.author, username)
                if comment.id not in replied_list and comment.author != username:
                    dt = datetime.utcnow()
                    userquery = matches.group('keywords').strip(identifiers)
                    ''' get the related entry in python docs.python.org '''
                    # doc = get_doc(userquery)
                    ''' Process query and format reply before submit comment '''
                    with open('result.txt', 'a', encoding='utf-8') as logs:
                        logs.write('''{0}: Found {1} from {2}: {3} 
                            in url: {4}\n'''.format(
                        dt, userquery, comment.author, comment.body, comment.id)
                    )
                    """comment.reply('''
                        Reply test: Hi {0}! I got your call at {1}, 
                        Found {2}.\n  Be right back with the related entry!
                    '''.format(comment.author, dt, userquery))
                    """
                    # mock reply 
                    print('''
                        Reply test: Hi {0}! I got your call at {1}, 
                        Found {2}.\n  Be right back with the related entry!
                    '''.format(comment.author, dt, userquery))
                    
                    ''' log this one as replied '''
                    print('Logged id[{0}] from {1}'.format(comment.id, comment.author))
                    replied_list.append(comment.id)
                    # print('Resuming after 60s...')
                    # time.sleep(60)
                ''' don't think this is needed? check if self replied '''
                # elif comment.author == username:
                    # print(comment.author, comment.body)
                    # replied_list.append(comment.id)
                # log.append(comment)
                ''' wait for sleep_interval to avoid flooding & heroku limit '''
                print('''
                    Skipped replied comment id [{}]. Resuming after 60s...
                    '''.format(comment.id))
                time.sleep(60)

def main():
    ''' capture exceptions '''
    try:
        ''' get replied list data '''
        # get_replied()
        search_sub(subreddit, 100)
    except ConnectionError as no_connection:
        print(no_connection)
        time.sleep(100)
        print('Reconnecting in 10secs...')
        search_sub(subreddit, 100)

if __name__ == '__main__':
    main()
