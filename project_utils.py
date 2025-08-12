# This is a collection of 
# cmdline UI (and other) code

import sys

# import to allow manipulation of json and jsonpath navigation of response from LLM:
import json, jsonpath_ng.ext as jsonpath
#LLM related imports:
from sentence_transformers import SentenceTransformer
# import to allow easy HTTP calls:
import requests
# prompt templates for LLM:
from prompt_templates import *
# rag text retrieval function:
from rag_similarity_helper import *

# import hard coded db config and localAI LLM url:
from connection_stuff import *

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


        
def insert_llm_prompt_response(prompt_embedding,prompt_text,llm_response_text,prompt_template):
    if isinstance(prompt_text, list):
        prompt_text = ' '.join(str(x) for x in prompt_text)
    llm_response_text = llm_response_text.strip()
    new_pk=None
    query = f'''INSERT INTO vdb.llm_history 
        (prompt_embedding, prompt_text, llm_response, star_rating, prompt_template)
        VALUES ('{prompt_embedding}', %s, %s, 3, %s) returning pk;'''
    args = (prompt_text, llm_response_text, prompt_template)
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query,args)
                new_pk = cur.fetchone()[0] 
    except Exception as e:
        print(f"❌ Error during SQL INSERT processing: {e}")
    return new_pk

# the query filters results using both the user-assigned star_rating_filter and 
# the semantic similarity of the prompt to prior stored prompts
# they must be threshold% semantically similar to be returned
def query_using_vector_similarity(incoming_prompt_vector,star_rating_filter,prompt_template):
    print(f"query_using_vector_similarity - using {prompt_template}")
    pk = None
    threshold = 80
    cached_response = ""
    similarity_percent=80
    query=f'''WITH target_vector AS (
        SELECT '{incoming_prompt_vector}'::vector AS ipv
    )
    SELECT pk,
    llm_response,
    star_rating,
    ROUND(
        GREATEST(0, LEAST(1, 1 - cosine_distance(prompt_embedding, ipv))) * 100,
        2
    ) AS "Percent Match"
    FROM llm_history, target_vector
    WHERE star_rating >= %s
    AND prompt_template = %s
    AND ROUND(
        GREATEST(0, LEAST(1, 1 - cosine_distance(prompt_embedding, ipv))) * 100,
        2
    ) > %s
    ORDER BY "Percent Match" DESC
    LIMIT 2;'''
    
    args = (star_rating_filter,prompt_template,threshold,)
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query,args)
                result = cur.fetchone()
                if result:
                    pk = result[0] #pk
                    print("\nFound at least one prior similar prompt:\n")
                    cached_response=result[1] # stored llm_response
                    cached_response = cached_response.strip()
                    similarity_percent=result[3]
                    print(f"  - llm response:\n {cached_response}\n\nStar Rating for LLM Response: {result[2]}, Prompt Similarity Percentage: {similarity_percent}%")
                else:
                    print("No matching data.")
    except Exception as e:
        print(f"❌ Error during SQL Vector Similarity processing: {e}")
    return {"pk": pk, "similarity_percent": similarity_percent, "cached_response": cached_response}

## This function is where we interact with the LLM 
# - providing a prompt that guides the behavior as well as 
# the question posed by the user:
def ask_llm(user_prompt,config_dict):
    template_func=config_dict.get("template_func")
    temperature=config_dict.get("temperature")
    rag=config_dict.get("rag")
    print(f"ask_llm system state: rag = {rag} template_func = {template_func} temperature = {temperature}")
    # a little prompt engineering is needed to get the answers in a usable format:
    # HERE IS WHERE your specification of a different prompt_template function as the third argument to this program takes effect:
    # example program startup where the template matching 'gang' is used:  (see code in prompt_templates.py)
    # python3 simpleLLM_with_cache.py 6 nostore gang
    if rag==True: #fetch additional information to include in prompt to LLM:
        prompt_vector=create_embedding(user_prompt)
        augmentation_text=rag_query_using_vector_similarity("public_customer_stories",prompt_vector)
        wrapped_prompt=template_func(augmentation_text,user_prompt) 
    else:
        wrapped_prompt=template_func(user_prompt) 

    llm_request_data = {"model": "tinyswallow-1.5b-instruct","response_format": {"type": "json"}, "messages": [{"role": "user", "content": f"{wrapped_prompt}"}], "temperature": temperature}
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

