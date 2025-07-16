# This is a collection of 
# cmdline UI code

import sys,getopt
# prompt templates for LLM:
from prompt_templates import *


### LLM / AI Setup ###
# Q: where is the LLM library? A: we are using a hosted 'localAI' server
# https://localai.io/ 
llm_chat_url = "http://localhost:6060/v1/chat/completions"

### CRDB connection setup ###
# Q: whare is the database? A: we assume a locally hosted insecure CRDB instance

db_config = {
    'host': 'localhost',
    'port': 26257,
    'dbname': 'vdb',
    'user': 'root'
}

# this value determines the accepted rating of a cached response to a prompt/question
# it should be possible for management / users to rate the responses they get in order to
# flag the bad ones and allow for new ones
# Ratings are between 1 and 5 where 5 is the best score 
# the default rating for cached responses is 3
# pass in a larger value to cause queries to fail (as of now all rows have a star_rating of 3):
star_rating_target = 3

# this value determines which prompt tenplate to send to the LLM - it can be overriden at runtime by the user as sys.argv[3]
template_func=TEMPLATE_MAP.get("base")

# this value determines the temperature used by the LLM - a larger value give the model more freedom to be creative
temperature = .45

#print(f' sys.argv length == {len(sys.argv)}')

if len(sys.argv) > 1:
    star_rating_target=int(sys.argv[1])
    print(f'You have set the star_rating filter to {star_rating_target}, lower-rated responses will be ignored')

# this flag determines if the program writes new embeddings and text responses to the database or skips that functionality
# you would set this to true in order to test interactions with the LLM and avoid poluting your database with nonsense 
nostore = False
if len(sys.argv) > 2:
    nostore=True
    print(f'You have set the nostore to {nostore}, if True, no new data will be stored in the database')

# this argument specifies the name of a prompt to use when invoking the LLM 
# example template_gang
if len(sys.argv) > 3:
    prompt_template=sys.argv[3].strip()
    template_func=TEMPLATE_MAP.get(prompt_template,template_base)
    print(f'You have set the prompt template to {template_func.__name__} the responses from the LLM will be impacted accordingly')
    sample_prompt = template_func("test")
    print(f'Here is the prompt to be used: \n{sample_prompt}')
    # if the LLM is supposed to represent a gangster, the temperature needs to be increased to allow creativity:
    if prompt_template=='gang':
        temperature=1.5


# bootstrap value, as we later check for the existence of user_input
user_input = "BEGIN"

# This string is used to separate areas of command line output: 
spacer = "\n**********************************************"

## this function displays the commandline menu to the user
## it offers the ability to end the program by typing 'end'
def display_menu():
    print(spacer)
    print('\tType: END   and hit enter to exit the program...\n')
    print('\tCommandline Instructions: \nType in your prompt/question as a single statement with no return characters... ')
    print('(only hit enter for the purpose of submitting your question)')
    print(spacer)
    # get user input/prompt/question:
    user_text = input('\n\tWhat is your question? (prompt):\t')
    if user_text =="END" or user_text =="end":
        print('\nYOU ENTERED --> \"END\" <-- QUITTING PROGRAM!!')
        exit(0)
    return (user_text)



