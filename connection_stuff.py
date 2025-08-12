# import driver for CRDB/postgres:
import psycopg 

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

