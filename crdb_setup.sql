-- enable vector indexing at the cluster level (assumes CRDB version 25.2 or higher)
SET CLUSTER SETTING feature.vector_index.enabled = true;

-- create our vdb (vector battleship) database:
CREATE DATABASE IF NOT EXISTS vdb;

-- switch to using the vdb database:
USE vdb;

-- dropping tables may be useful if you want to clean up:
drop table IF EXISTS vdb.llm_history;

-- look at what tables exist in your database:
SHOW tables;

-- create the llm_history table:  
-- note the use of the vector prompt_embedding
-- note the use of star_rating to encourage limiting results to only desired ratings
CREATE TABLE IF NOT EXISTS vdb.llm_history(
   pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
   prompt_embedding VECTOR(768),
   prompt_text string,
   llm_response string,
   prompt_template string NOT NULL DEFAULT 'template_base' CHECK (prompt_template IN ('template_base','template_music','template_gang','template_poet','template_rag','template_sql_tool')),
   star_rating smallint NOT NULL DEFAULT 3 CHECK (star_rating BETWEEN 1 AND 5),
   VECTOR INDEX (star_rating,prompt_template,prompt_embedding vector_cosine_ops) -- non-default cosine nearest neighbor support (default is L2 for KNN)
);

-- create the llm_enrichment table:  
-- data in this table is used to augment prompts sent to an LLM
-- note the use of the vector chunk_embedding
-- a sophisticated chunking strategy could exploit the 'subject_matter' attribute for faster lookups
CREATE TABLE IF NOT EXISTS vdb.llm_enrichment(
   pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
   subject_matter string,
   chunk_embedding VECTOR(768),
   text_chunk string,
   VECTOR INDEX (subject_matter, chunk_embedding vector_cosine_ops) -- non-default cosine nearest neighbor support (default is L2 for KNN)
);

-- just a simple check for any rows 
SELECT COUNT(*) from vdb.llm_history;

-- just a simple check for one existing llm_response:
SELECT llm_response from vdb.llm_history ORDER BY random() LIMIT 1;