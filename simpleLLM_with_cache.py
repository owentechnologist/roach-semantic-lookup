# to run this example you will need the following :
""" 
An active enpoint running localAI as a REST service
Example:
curl http://34.148.227.54:8080/v1/chat/completions -H "Content-Type: application/json" -d '{
  "model": "tinyswallow-1.5b-instruct",
  "messages": [{"role": "user", "content": "Who was Abe Lincoln."}],
  "temperature": 0.3
}'
"""

"""
A running instance of CockroachDB version 25.2 or higher
"""
# this version of the program hard-codes the following 2 connection configurations
# 1. the url to connect to localhost insecure crdb: postgresql://root@localhost:26257/vdb?sslmode=disable
# 2. the url to connect to localhost localAI http://localhost:6060/v1/chat/completions
# sample execution of this python program: 
""" 
python simpleLLM_with_cache.py 
python simpleLLM_with_cache.py  

"""

# import driver for CRDB:
import psycopg 
# import to allow easy HTTP calls:
import requests
# import to allow manipulation of json and jsonpath navigation of response from LLM:
import json, jsonpath_ng.ext as jsonpath
#LLM related imports:
from sentence_transformers import SentenceTransformer
#general imports: 
import time,uuid
### cmdline_utils==General Setup &
# UI and Redis connection functions: ###
from cmdline_utils import *
from prompt_templates import *

# edit (increase) this value to cause queries to fail (as of now all rows have a star_rating of 3):
star_rating_target = 3 #default value 

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
        
def insert_llm_prompt_response(prompt_embedding,prompt_text,llm_response_text):
    if isinstance(prompt_text, list):
        prompt_text = ' '.join(str(x) for x in prompt_text)
    llm_response_text = llm_response_text.strip()
    query = f'''INSERT INTO vdb.llm_history 
        (prompt_embedding, prompt_text, llm_response, star_rating)
        VALUES ('{prompt_embedding}', %s, %s, 3);'''
    args = (prompt_text, llm_response_text)
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query,args)
    except Exception as e:
        print(f"❌ Error during SQL INSERT processing: {e}")
    return 'insert function returning...'

# the query filters results using both the user-assigned star_rating_filter and 
# the semantic similarity of the prompt to prior stored prompts
# they must be 50% semantically similar to be returned
def query_using_vector_similarity(incoming_prompt_vector,star_rating_filter):
    return_results = 'null'
    query=f'''WITH target_vector AS (
        SELECT '{incoming_prompt_vector}'::vector AS ipv
    )
    SELECT
    llm_response,
    star_rating,
    ROUND(
        GREATEST(0, LEAST(1, 1 - cosine_distance(prompt_embedding, ipv))) * 100,
        2
    ) AS "Percent Match"
    FROM llm_history, target_vector
    WHERE star_rating >= %s
    AND cosine_distance(prompt_embedding, ipv) <= 1
    ORDER BY "Percent Match" DESC
    LIMIT 2;'''
    args = (star_rating_filter,)
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query,args)
                results = cur.fetchall()
                if results:
                    return_results = results
                    print("\nFound at least one prior similar prompt:\n")
                    for row in results:
                        val=row[0] # stored llm_response
                        val = val.strip()
                        print(f"  - llm response:\n {val}\n\nStar Rating for LLM Response: {row[1]}, Prompt Similarity Percentage: {row[2]}%")
                else:
                    print("No matching data.")
                    nearby_ship = False
    except Exception as e:
        print(f"❌ Error during SQL Vector Similarity processing: {e}")
    return return_results

## This function is where we interact with the LLM 
# - providing a prompt that guides the behavior as well as 
# the question posed by the user:
def ask_llm(question):
    # a little prompt engineering is needed to get the answers in a usable format:
    # HERE IS WHERE you could call a different prompt_template function:
    template_=template_base(question) 
    #template_=template_cockroach(question)
    #template_=template_music(question)
    #template_=template_gang(question)
    #template_=template_poet(question)

    llm_request_data = {"model": "tinyswallow-1.5b-instruct","response_format": {"type": "json"}, "messages": [{"role": "user", "content": f"{template_}"}], "temperature": 0.25}
    print(f"DEBUG: we are sending this to the LLM:\n {llm_request_data}")
    headers =  {"Content-Type": "application/json"}    
    myResponse = requests.post(llm_chat_url,json=llm_request_data,headers=headers )
    decoded_json = myResponse.content.decode('utf-8')
    json_data = json.loads(decoded_json)
    print(f"\nDEBUG: {json_data.keys()}")    

    # provide a default string for the reply in case LLM fails:
    response_s = "Unknown (Not Answered)"

    # Specify the path to be used within the JSON returned from the LLM: 
    json_query = jsonpath.parse("choices[0].message.content")
    # thought: how could we use jsonpath.parse to extract the count of tokens used?

    ## extract the value located at the path we selected in our json_query
    for match in json_query.find(json_data):
        response_s=match.value
    return response_s


# UI loop: (if user responds with "END" - program ends)
while True:    
    sentences = [display_menu()]
    user_input = sentences
    model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
    
    # create the numpy array encoding representation of the sentences/prompt:
    prompt_ndarr = model.encode(sentences[0])
    # convert it to a format acceptable to crdb:
    prompt_embedding = prompt_ndarr.tolist()
    # pass the user text/prompt to the LLM Chain and print out the response: 
    # also, check for a suitable cached response
    if user_input:
        # we are interested in seeing how long it takes to query using Vector indexes: 
        start_time=time.perf_counter()
        # now we can search for semantically similar prompt(s)
        # this function expects a user-created star_rating from 1 to 5 (5 star is best)
        #print('before DB vector query...')
        results = query_using_vector_similarity(prompt_embedding,star_rating_target)
        #print(f'after DB vector query...  results type == {type(results)}')
        llm_response = ""
        if 'null'==results:
            print('\n No suitable prior response has been found.  Generating new Response...\n')
            # create a new LLM-generated result as the answer:            
            llm_response = ask_llm(user_input) 
            #print('before DB insert...')
            insert_llm_prompt_response(prompt_embedding,user_input,llm_response)
            #print('after DB insert...')
        # output whatever the result is to the User Interface:
        print(f'{spacer}\n{llm_response}{spacer}\n')
        uparrows = " ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ \n"
        print(f'\t{uparrows}\tElapsed Time to respond to user prompt was: {(time.perf_counter()-start_time)*1} seconds\n')
