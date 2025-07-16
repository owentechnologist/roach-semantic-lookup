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
   star_rating smallint NOT NULL DEFAULT 3 CHECK (star_rating BETWEEN 1 AND 5),
   VECTOR INDEX (star_rating,prompt_embedding)
);

-- just a simple check for any rows 
SELECT COUNT(*) from vdb.llm_history;

-- just a simple check for one existing llm_response:
SELECT llm_response from vdb.llm_history ORDER BY random() LIMIT 1;