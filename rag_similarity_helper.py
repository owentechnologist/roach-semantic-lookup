from project_utils import *
# import hard coded db config and localAI LLM url:
from connection_stuff import get_connection

#rag_similarity_helper.py
## This function enables: 
# The retrieval of chunks of text from a vectorDB based on their relevance to an incoming vectorized prompt
# in addition, it opens up the limiting of access by visibility
# this naive demo always uses public visibility as a filter
# a richer impl would take classification_description as an additional arg to the function

# the query targets a separate table called: llm_enrichment which contains chunked reference/memory text
# the semantic similarity of the prompt is used to fetch additional information that can be used to augment the prompt for an llm  
# they must be <threshold%> semantically similar to be returned
# returns a dictionary containing the content and pk of the 
def rag_query_using_vector_similarity(subject_matter, incoming_prompt_vector):
    classification_description='public' #ALERT! hard coded, naive example
    pk = None
    val = "Suggest a web search to get the missing information' <h2><em>..."
    threshold = 35.0
    oldquery=f'''WITH 
    target_vector AS (
        SELECT '{incoming_prompt_vector}'::vector AS ipv
    ),
    visibility_id AS (
        SELECT pk FROM visibility_classification WHERE classification_description=%s
    )
    SELECT le.pk,
    le.text_chunk,
    ROUND(
        GREATEST(0, LEAST(1, 1 - cosine_distance(le.chunk_embedding, ipv))) * 100,
        2
    ) AS "Percent Match"
    FROM llm_enrichment le, target_vector tv, visibility_id vi
    WHERE vi.pk IS NOT NULL 
    AND (le.subject_matter = %s OR le.subject_matter like %s)
    AND (GREATEST(0, LEAST(1, 1 - cosine_distance(le.chunk_embedding, ipv))) * 100) > %s
    ORDER BY "Percent Match" DESC
    LIMIT 1;'''
    # oldQuery above uses function call cosine_distance 
    # query below uses cosine distance operator <=> (only available CRDB >= 25.3)
    query=f'''WITH 
    target_vector AS (
        SELECT '{incoming_prompt_vector}'::vector AS ipv
    ),
    visibility_id AS (
        SELECT pk FROM visibility_classification WHERE classification_description=%s
    )
    SELECT le.pk,
    le.text_chunk,
    ROUND(
        GREATEST(0, LEAST(1, 1 - (le.chunk_embedding <=> ipv))) * 100,
        2
    ) AS "Percent Match"
    FROM llm_enrichment le, target_vector tv, visibility_id vi
    WHERE vi.pk IS NOT NULL 
    AND (le.subject_matter = %s OR le.subject_matter like %s)
    AND (GREATEST(0, LEAST(1, 1 - (le.chunk_embedding <=> ipv))) * 100) > %s
    ORDER BY "Percent Match" DESC
    LIMIT 1;'''

    args = (classification_description,subject_matter,'public%',threshold,)
    print(f'\n***DEBUG***\ncalling DB and filtering on: {classification_description}, {subject_matter}, {threshold}% similarity \n')
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query,args)
                result = cur.fetchone()
                if result:
                    pk = result[0] #pk
                    print("\nFound at least one relevant chunk of text:\n")
                    val=result[1] # stored text chunk
                    val = val.strip()
                    print(f"  - text chunk:\n {val},\n\n Prompt Similarity Percentage: {result[2]}%")
                else:
                    print("No matching embedding data stored in the table vdb.llm_enrichment ....")
    except Exception as e:
        print(f"❌ DB Error during rag_query_using_vector_similarity processing: {e}")
    
    #return the text so it can be passed to the LLM and used to inform the response
    print(f'\n***DEBUG***\nRAG response from calling CRDB:\n {val}')
    return val,pk

        
