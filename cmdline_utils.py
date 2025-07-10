# This is a collection of 
# cmdline UI code

import sys,getopt


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
if len(sys.argv) > 2:
    star_rating_target=int(sys.argv[2])
    print(f'You have set the star_rating filter to {star_rating_target}, lower-rated responses will be ignored')

# this flag determines if the program writes new embeddings and text responses to the database or skips that functionality
# you would set this to true in order to test interactions with the LLM and avoid poluting your database with nonsense 
nostore = False
if len(sys.argv) > 3:
    nostore=True
    print(f'You have set the nostore to {nostore}, if True, no new data will be stored in the database')

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



