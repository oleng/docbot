#!/usr/bin/env python
""""
[MotherBot] Reddit bot by /u/num8lock
Desc:       docbot module for MotherBot
version:    v.0.1
git:        

Codes based on many reddit bot creators 
/u/redditdev
"""
# delete ignore.motherbot when using heroku and use env
# variables instead
import ignore.motherbot as motherbot


sub = 'bot_testing'

r = motherbot.login()
print('Logged in...')

