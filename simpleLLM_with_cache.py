# to run this example you will need the following :
""" 
An active enpoint running localAI as a REST service
Example:
curl http://34.148.227.54:8080/v1/chat/completions -H "Content-Type: application/json" -d '{
  "model": "tinyswallow-1.5b-instruct",
  "messages": [{"role": "user", "content": "Who was Abe Lincoln."}],
  "temperature": 0.45
}'
"""

"""
A running instance of CockroachDB version 25.2 or higher
"""
# this version of the program hard-codes the following 2 connection configurations
# 1. the url to connect to localhost insecure crdb: postgresql://root@localhost:26257/vdb?sslmode=disable
# 2. the url to connect to localhost localAI http://localhost:6060/v1/chat/completions
# Edit cmdline_utils.py to adjust these hard coded connection details
# sample executions of this python program: 
""" 
python simpleLLM_with_cache.py 
python simpleLLM_with_cache.py <star_rating_filter> 
python simpleLLM_with_cache.py 4 nostore
python simpleLLM_with_cache.py 4 nostore poet
"""

#general imports: 
import time
### cmdline_utils==General Setup &

# prompt templates for LLM:
from prompt_templates import *
# UI and Redis connection functions: ###
from project_utils import *

# bootstrap value, as we later check for the existence of user_input
user_input = "BEGIN"

# These strings are used to separate areas of command line output: 
spacer = "\n**********************************************"
uparrows = "\n ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ "

def check_star_rating(pk):
    txt = input(f'\n{spacer}\nFrom 1 to 5 (where 5 is best) please rate that response: \t')
    star_rating=int(txt)
    update_star_rating(star_rating,pk)

def update_star_rating(new_rating,pk):
    query = '''update vdb.llm_history SET star_rating=%s where pk=%s;'''
    args = (new_rating, pk)
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query,args)
    except Exception as e:
        print(f"❌ Error during SQL UPDATE processing: {e}")
    return 'update function returning...'

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


# UI loop: (if user responds with "END" - program ends)
def main_routine():
    while True:    
        sentences = [display_menu()]
        user_input = sentences
        prompt_embedding = create_embedding(sentences)
        # pass the user text/prompt to the LLM Chain and print out the response: 
        # also, check for a suitable cached response
        if user_input:
            # we are interested in seeing how long it takes to query using Vector indexes: 
            start_time=time.perf_counter()
            llm_interrupt_time=0
            # now we can search for semantically similar prompt(s)
            # this function expects a user-created star_rating from 1 to 5 (5 star is best)
            #print('before DB vector query...')
            pk = query_using_vector_similarity(prompt_embedding,star_rating_target,template_func.__name__).get("pk")
            #print(f'after DB vector query...  results type == {type(results)}')
            llm_response = ""
            if None==pk:
                print('No suitable prior response has been found.')
                #print(f'DEBUG: VALUES CHECK: nostore=={nostore} pk=={pk}')
                print('\n Generating new Response...\n')
                # create a new LLM-generated result as the answer:            
                llm_interrupt_time=time.perf_counter()
                config_dict={"template_func":template_func,"temperature":temperature,"rag":rag}
                llm_response = ask_llm(user_input,config_dict) 
                llm_interrupt_time=time.perf_counter()-llm_interrupt_time
                if nostore==False:
                    #print('before DB insert...')
                    pk = insert_llm_prompt_response(prompt_embedding,user_input,llm_response,template_func.__name__)
                    #print('after DB insert...')
            # output whatever the result is to the User Interface:
            print(f'{spacer}\n{llm_response}{spacer}\n')
            duration=(time.perf_counter()-(start_time+llm_interrupt_time))*1
            print(f'\t{uparrows}\tElapsed Time spent querying database was: {duration} seconds\n')
            print(f'\t{uparrows}\tElapsed Time spent querying LLM was: {llm_interrupt_time} seconds\n')
            if not None == pk:
                check_star_rating(pk)

# this value determines the accepted rating of a cached response to a prompt/question
# it should be possible for management / users to rate the responses they get in order to
# flag the bad ones and allow for new ones
# Ratings are between 1 and 5 where 5 is the best score 
# the default rating for cached responses is 3
# pass in a larger value to cause queries to fail (as of now all rows have a star_rating of 3):
star_rating_target = 3

# this value determines which prompt template to send to the LLM - it can be overriden at runtime by the user as sys.argv[3]
template_func=TEMPLATE_MAP.get("base")

# this variable determines the temperature used by the LLM - a larger value give the model more freedom to be creative
temperature = .45

# this variable determines if the LLM gets fed additional data retrieved from the database ala the RAG pattern:
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

# this argument specifies the name of a prompt to use when invoking the LLM 
# example template_gang
if len(sys.argv) > 3:
    template_key=sys.argv[3].strip()
    template_result=configure_temperature_and_template(template_key=template_key)
    template_func=template_result.get("template_func")
    rag=template_result.get("rag")
    if rag==True:
        sample_prompt = template_func(augmentation_text="This text augments the prompt sent to the LLM.",user_prompt="this is the original prompt")
    else:
        sample_prompt = template_func("this is the original prompt")
    print(f'Here is the prompt to be used: \n{sample_prompt}')


# --- Example usage ---
if __name__ == "__main__":
    main_routine()
