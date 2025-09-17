# import to allow manipulation of json and jsonpath navigation of response from LLM:
import json
from project_utils import *

## TO DELETE OLD ENRICHMENT DATA AND LOAD ONLY WHAT's IN THE ragdata.json file:
## Use an additional argument when launching this ... example:
## python3 load_rag_data.py T

# here we create the embeddings and load the data from the json file into the database: 
def insert_text_chunk(text_embedding,subject_matter,similarity_text,text_chunk):
    if isinstance(subject_matter, list):
        subject_matter = ' '.join(str(x) for x in subject_matter)
    subject_matter = subject_matter.strip()
    if isinstance(text_chunk, list):
        text_chunk = ' '.join(str(x) for x in text_chunk)
    if isinstance(similarity_text, list):
        similarity_text = ' '.join(str(x) for x in similarity_text)
    text_chunk = text_chunk.strip()
    similarity_text = similarity_text.strip()
    new_pk=None
    query = f'''INSERT INTO vdb.llm_enrichment 
        (chunk_embedding, subject_matter, similarity_text,text_chunk)
        VALUES ('{text_embedding}', %s, %s, %s) returning pk;'''
    args = (subject_matter, similarity_text,text_chunk)
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query,args)
                new_pk = cur.fetchone()[0] 
    except Exception as e:
        print(f"❌ DB Error during insert_text_chunk processing: {e}")
    return new_pk

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
        {"subject_matter": "public_customer_stories","related_content_id":"e4327a69-b5d6-4ce3-8e45-b4cae0095282","content_summary_for_prompt_similarity": "Question: Who is Shipt? Answer: Shipt is a company that switched databases from postgres to cockroach","text_chunk": "Shipt, a logistics and delivery company acquired by Target, struggled with their prior postgres database in keeping delivery drivers connected and wanted to avoid unnecessary dependencies and cost to their business.  They selected CockroachDB to act as their database and found success.  Shipt values the compatibiility of CRDB with Postgresql. They found the transition to CRDB to be simple."},
  ]
}
'''
def read_json_file():
    with open('ragdata.json', 'r') as file:
        data = json.load(file)
        # Initialize lists to store the extracted data
    subject_matters = []
    similarity_texts = []
    text_chunks = []
    # Access the list of dictionaries using the key "text_chunks"
    for entry in data.get("text_chunks", []):        
        # Extract the values and append them to the respective lists
        similarity_texts.append(entry.get('content_summary_for_prompt_similarity', ''))
        subject_matters.append(entry.get('subject_matter', ''))
        text_chunks.append(entry.get('text_chunk', ''))    
        
    return subject_matters, similarity_texts, text_chunks

# used as initialization through the use of the LOAD instruction 
# (commandline only) 
#  or if additional text chunks are added to the json file:
# to prevent duplicates this simple sql can be used:
#  delete from vdb.llm_enrichment where 1=1
def load_augmentation_text():
    subject_matters, similarity_texts, text_chunks = read_json_file()
    for i in range(len(subject_matters)):
        similarity_text=similarity_texts[i]
        search_embedding = create_embedding(similarity_text)
        llm_info_text=text_chunks[i]
        insert_text_chunk(subject_matter=subject_matters[i],similarity_text=similarity_text,text_chunk=llm_info_text,text_embedding=search_embedding)
    return 

def delete_rag_data():
    print('DELETING EXISTING RAG ENRICHMENT DATA...')
    query = f'''TRUNCATE vdb.llm_enrichment;'''
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
    except Exception as e:
        print(f"❌ DB Error during TRUNCATE llm_enrichment: {e}")

# --- Example usage ---
if __name__ == "__main__":
    if(len(sys.argv)>1):
        #An empty string ("") evaluates to False
        # any other value evaluates to True
        delete_old=bool(sys.argv[1])
        if delete_old==True:
            delete_rag_data()
    print("\nLOADING RAG DATA FROM ragdata.json into the vdb.llm_enrichment table...")
    load_augmentation_text()
    print("\nDONE!")
    