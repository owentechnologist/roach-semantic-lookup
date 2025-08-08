# This is a collection of 
# cmdline UI (and other) code

import sys,getopt
# import driver for CRDB/postgres:
import psycopg 
import json, jsonpath_ng.ext as jsonpath
#LLM related imports:
from sentence_transformers import SentenceTransformer
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

def get_connection():
        # use unpacking operator ** to turn dict to separate args:
        return psycopg.connect(**db_config)


# this value determines the accepted rating of a cached response to a prompt/question
# it should be possible for management / users to rate the responses they get in order to
# flag the bad ones and allow for new ones
# Ratings are between 1 and 5 where 5 is the best score 
# the default rating for cached responses is 3
# pass in a larger value to cause queries to fail (as of now all rows have a star_rating of 3):
star_rating_target = 3

# this value determines which prompt tenplate to send to the LLM - it can be overriden at runtime by the user as sys.argv[3]
template_func=TEMPLATE_MAP.get("base")

# this variable determines the temperature used by the LLM - a larger value give the model more freedom to be creative
temperature = .45

# this variable determines if the LLM gets fed additional data retreived from the database ala the RAG pattern:
# it gets set to True when the 'aug' (for augmented) template is specified 
rag=False

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

def configure_temperature_and_template(template_key):
    temperature=.45
    rag=False
    # if the LLM is supposed to represent a gangster, the temperature needs to be increased to allow creativity:
    if template_key=='gang':
        temperature=1.5
    # if the LLM is supposed to generate sql, the temperature needs to be decreased to enforce stricter syntax:
    elif template_key=='sql':
        temperature=.15
    # if the LLM is supposed to receive additional information/an augmented prompt, we set the rag variable to True:
    elif template_key=='rag':
        rag=True
    template_func=TEMPLATE_MAP.get(template_key,template_base)
    print(f'You have set the prompt template to {template_func.__name__} the responses from the LLM will be impacted accordingly')
    
    return { "template_func": template_func, "temperature": temperature, "rag": rag}

# this argument specifies the name of a prompt to use when invoking the LLM 
# example template_gang
if len(sys.argv) > 3:
    template_key=sys.argv[3].strip()
    template_func=configure_temperature_and_template(template_key=template_key)
    if rag==True:
        sample_prompt = template_func(augmentation_text="This text augments the prompt sent to the LLM.",user_prompt="this is the original prompt")
    else:
        sample_prompt = template_func("this is the original prompt")
    print(f'Here is the prompt to be used: \n{sample_prompt}')


# bootstrap value, as we later check for the existence of user_input
user_input = "BEGIN"

# These strings are used to separate areas of command line output: 
spacer = "\n**********************************************"
uparrows = "\n ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ "

## this is designed to be executed before the main interactions with the LLM:
## The data is loaded from the file: ragdata.json 
## the sample provided could have its contents replaced with whatever makes sense for your use case
## there is a Goldilocks effect with the length of text used in an embedding 
# - too short and no context, too long and no focus for LLM
# the use of the subject_matter as a filter is powerful for limiting access and setting up guard rails
## the format used for this example is:
'''
{
  "text_chunks":[
    {"subject_matter": "public_something", "text_chunk":"the text that informs the LLM for this instance of the subject_matter"},
    {"subject_matter": "private_something", "text_chunk":"different text that informs the LLM for this other instance of some subject_matter"}
  ]
}
'''
def read_json_file():
    with open('ragdata.json', 'r') as file:
        data = json.load(file)
        # Initialize lists to store the extracted data
    subject_matters = []
    text_chunks = []
    # Access the list of dictionaries using the key "text_chunks"
    for entry in data.get("text_chunks", []):        
        # Extract the values and append them to the respective lists
        subject_matters.append(entry.get('subject_matter', ''))
        text_chunks.append(entry.get('text_chunk', ''))    
        
    return subject_matters, text_chunks

# here we create the embeddings and load the data from the json file into the database: 
def insert_text_chunk(text_embedding,subject_matter,text_chunk):
    if isinstance(subject_matter, list):
        subject_matter = ' '.join(str(x) for x in subject_matter)
    subject_matter = subject_matter.strip()
    if isinstance(text_chunk, list):
        text_chunk = ' '.join(str(x) for x in text_chunk)
    text_chunk = text_chunk.strip()
    new_pk=None
    query = f'''INSERT INTO vdb.llm_enrichment 
        (chunk_embedding, subject_matter, text_chunk)
        VALUES ('{text_embedding}', %s, %s) returning pk;'''
    args = (subject_matter, text_chunk)
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query,args)
                new_pk = cur.fetchone()[0] 
    except Exception as e:
        print(f"❌ DB Error during insert_text_chunk processing: {e}")
    return new_pk

# used as initialization through the use of the LOAD instruction 
# (commandline only) 
#  or if additional text chunks are added to the json file:
# to prevent duplicates this simple sql can be used:
#  delete from vdb.llm_enrichment where 1=1
def load_augmentation_text():
    subject_matters, text_chunks = read_json_file()
    for i in range(len(subject_matters)):
        some_text=text_chunks[i]
        some_embedding = create_embedding(some_text)
        insert_text_chunk(subject_matter=subject_matters[i],text_chunk=some_text,text_embedding=some_embedding)
    return 

# a helper function that takes in a string and returns a vector embedding suitable for 
# storing in any vectorDB (CRDB or postgres etc) as a searchable vector    
def create_embedding(some_text):
    #make certain we have an array to work with where the first element is the full text:
    if type(some_text) != list:
        wrap_array=[some_text,]
    else:
        wrap_array=some_text
    
    #print(f'the first element of the list being embedded is: {wrap_array[0]}')
    model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')    
    # create the numpy array encoding representation of the sentences/prompt:
    prompt_ndarr = model.encode(wrap_array[0])
    # convert it to a format acceptable to crdb:
    prompt_embedding = prompt_ndarr.tolist()
    return prompt_embedding

## this function displays the commandline menu to the user
## it offers the ability to end the program by typing 'end'
## it offers the ability to load augmentation text into the DB for RAG use
def display_menu():
    print(spacer)
    print('\tType: END   and hit enter to exit the program...\n')
    print(spacer)
    print('\tType: LOAD   and hit enter to load augmentation text into the database...\n')

    print('\tCommandline Instructions: \nType in your prompt/question as a single statement with no return characters... ')
    print('(only hit enter for the purpose of submitting your question)')
    print(spacer)
    # get user input/prompt/question:
    user_text = input('\n\tPlease provide a command or question (prompt):\t')
    if user_text =="END" or user_text =="end":
        print('\nYOU ENTERED --> \"END\" <-- QUITTING PROGRAM!!')
        exit(0)
    if user_text =="LOAD" or user_text =="load":
        print('\nYOU ENTERED --> \"LOAD\" <-- loading text data to augment LLM responses...')
        load_augmentation_text()
        exit(0)
    return (user_text)



