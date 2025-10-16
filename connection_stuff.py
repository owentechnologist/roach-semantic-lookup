# import driver for CRDB/postgres:
import psycopg 
import os

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

# to utilize certs set the env variable SECURE_CRDB=true
# SECURE_CRDB=true
CERTDIR = '/Users/owentaylor/.cockroach-certs'
db_config_secure = {
    'host': 'localhost',
    'port': 26257,
    'dbname': 'vdb',
    'user': 'root',
    # SSL parameters:
    'sslmode': 'verify-full',         # or 'verify-full' if your host matches the cert SAN
    'sslrootcert': f'{CERTDIR}/ca.crt',
    'sslcert': f'{CERTDIR}/client.root.crt',
    'sslkey': f'{CERTDIR}/client.root.key',
    'connect_timeout': 10,
}

def get_connection():
    if(os.getenv("SECURE_CRDB", "false")=='true'):
        print('GETTING SECURE CONNECTION...')
        connection = psycopg.connect(**db_config_secure)
    else:
        print('GETTING NON-SECURE (PLAIN) CONNECTION...')
        connection = psycopg.connect(**db_config)
        # use unpacking operator ** to turn dict to separate args:
    assert connection is not None, "get_connection() returned None (connection failed)"
    return connection

