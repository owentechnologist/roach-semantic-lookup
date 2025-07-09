# roach-semantic-lookup
This example calls an LLM, stores the LLM response as text, along with both a vector embedding of the prompt and the text of the prompt used. The datastore used is CRDB.  The example also showcases searching for a prompt using Vector Search in order to avoid repeated calls to the LLM.  

## This example showcases a pattern known as semantic caching.

non-cached workflow when interacting with an LLM:

```
A: (UserPrompt as text is generated/accepted by system) 
B: Call LLM API with UserPrompt as text
C: (LLMResponse as Text is returned to user)
```
![Direct Call to LLM](./llm_direct.png)

Semantic caching workflow Successful match:

```
start workflow
A: (UserPrompt as text is generated/accepted by system) 
B: (UserPrompt as embedding is generated) 
C: CRDB Vector Similarity Query issued to check for existing responses to same semantic prompt 
If 
   Match to an existing stored UserPrompt Embedding exists : 
   D: Fetch Associated Stored LLM Text response and return to user
end workflow
```
![Query DB for similar query and existing response](./semantic_cache_hit.png)


Semantic caching workflow No match:

```
start workflow
A: (UserPrompt as text is generated/accepted by system) 
B: (UserPrompt as embedding is generated) 
C: CRDB Vector Similarity Query issued to check for existing responses to same semantic prompt 
If 
    No Match to an existing stored UserPrompt Embedding exists : 
    D: Call LLM API with UserPrompt as text 
    E:  Store UserPrompt Embedding along with userPrompt as text and LLMResponse as Text in CRDB
    F:  Return LLM Text response to user
end workflow
```

![Query DB fail](./semantic_cache_miss.png)

## This example Uses https://localai.io/ and CockroachDB to demonstrate basic Semantic Caching of responses to user prompts made to an LLM.

Again: This project is an example of using CRDB Vector Similarity Search/Queries with Python

To run the example, which utilizes CRDB Vector Similarity Search Queries, you will need a connection to a Large Language Model (LLM) and a connection to CRDB version 25.2.1 or higher. 

## install and Initialize a cockroach database to act as a vectorDB:


** download cockroachdb binary (you can use a single instance for testing) 

for mac you do:
```
brew install cockroachdb/tap/cockroach
```

You can then check for location/existence of cockroachDB:
```
which cockroach
```

<em> See full instructions here:  https://www.cockroachlabs.com/docs/v25.2/install-cockroachdb-mac.html 

(There are options there for Linux and Windows as well)
</em>

## You can start a single node instance of cockroachDB in the following way:

to keep things as simple as possible, start an instance requiring no TLS (Transport Layer Security):

```
cockroach start-single-node --insecure --accept-sql-without-tls --background
```

<em>See full instructions here:  https://www.cockroachlabs.com/docs/stable/cockroach-start-single-node  </em>

By default:

This local instance of cockroachDB will run listening on port 26257 (for SQL and commandline connections)

This local instance will also listen on port 8080 with its web-browser-serving dbconsole UI 

## From a separate shell you can connect to this instance, create a database and the tables needed to begin:

to execute all the SQL commands needed plus some test queries from the root of this project do:
```
cockroach sql --insecure -f crdb_setup.sql
```

## thoughts on calculating vector distances in CRDB: For Semantic Search against text embeddings we use the function: cosine_distance(vec1,vec2)
```
-- some useful calculations: (the larger the number the greater the distance between the vectors)
-- <= 0.33 filters is roughly ~75%+ similarity or better
-- <= 1 filters to ~50%+ similarity or better
-- <= 4 corresponds to ~20% match or higher
-- filter on percentage match option: 
-- cosine_distance(vec1,vec2)
```

## the essential query we will use to check for a semantic match to an incoming prompt will be:

```
WITH target_vector AS (
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
    LIMIT 2;
    ```

If you wish to execute other sql -- The following command connects using the provided SQL CLI:

```
cockroach sql --insecure
```

## Python-preparation Steps for running the samples on your dev machine:


1. Create a virtual environment:

```
python3 -m venv roachsc
```

2. Activate it:  [This step is repeated anytime you want this venv back]

```
source roachsc/bin/activate
```

On windows you would do:

```
roachsc\Scripts\activate
```
If no permission in Windows
 The Fix (Temporary, Safe, Local):
In PowerShell as Administrator, run:
```

Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```
Then confirm with Y when prompted.

3. Python will utilize this requirements.txt in the project:

```
psycopg[binary]>=3.0
etc ...
```

4. Install the libraries: [should only be necesary to do this one time per environment, but I found I needed to execute 2x to get psycopg installed]

```
pip3 install -r requirements.txt
```

5. SEVERAL THINGS ARE HARD CODED IN THIS EXAMPLE! (localhost for both crdb and localAI)
Edit your local copy of the code as you like and run the program.  Fix it as necessary to get the behavior you want ( see below for possible prompt engineering options )

```
python3 simpleLLM_with_cache.py 
```

* The example will call an LLM and display the response, as well as display the prompt sent to the LLM 

* To enable semantic caching the prompt needs to be stored in CRDB in its embedded form so that Vector Search can find it - to enable that behavior uncomment line FIXME

* Prompt engineering options: (note if you fetch a CRDB stored result, the LLM never gets called and the prompt engineering has no effect)
You may wish to force-fail the matching query by demanding a higher star_rating (around line 41)

## At Around line 115 in the file: simpleLLM_with_cache.py 
## You can try your hand at prompt engineering by playing with the alternate templates provided in the file: prompt_templates.py: ( the user input can be couched in such a template to modify the output of the LLM )
comment/uncomment the code to test different prompts:
```
    template_=template_base(question) 
    #template_=template_music(question)
    #template_=template_gang(question)
    #template_=template_poet(question)
```

6. When you are done using this environment you can deactivate it:

```
deactivate
```




