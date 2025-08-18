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

-- create the llm_history table:  (this is a quick 'cache' example)
-- NOT_IMPLEMENTED: (limiting the cached results to certain users/sessions)
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

-- entering the world of dynamic augmentation: guardrails and permissioning:
CREATE TABLE IF NOT EXISTS vdb.visibility_classification(
   pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
   classification_description string NOT NULL CHECK (classification_description IN ('internal_exec','internal_mngmnt','internal_general','private_session','public')),
   classification_int_value smallint NOT NULL CHECK (classification_int_value BETWEEN 0 AND 4)
);

-- metadata table that points to related data when desired/required
-- note that all attributes except visibility are many to many
-- whether to constrain access at the individual content entry level or not is debatable 
-- this example uses this related content level as the gatekeeper
-- SCENARIO: non-paying user gets zero access to any non-public visible data
CREATE TABLE IF NOT EXISTS vdb.related_content(
   pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
   image_uris_xref_id  UUID,
   video_uris_xref_id  UUID,
   research_text_uris_xref_id UUID,
   researchers_xref_id UUID, 
   reviewers_xref_id UUID,
   visibility_classification_id UUID NOT NULL REFERENCES vdb.visibility_classification(pk)
);

-- queries will uncover the UUID by 
-- SELECT pk FROM visibility_classification WHERE classification_description=public
INSERT INTO vdb.visibility_classification 
(classification_description,classification_int_value) 
VALUES ('internal_exec', 0),
  ('internal_mngmnt', 1),
  ('internal_general', 2),
  ('private_session', 3),
  ('public', 4);

-- insert (mostly) empty rows with public visibility so relations function as needed
-- JSON doc has hard-coded UUIDs that expect to match these rows:
WITH visibility AS (
     SELECT pk as visibility_pk FROM visibility_classification WHERE classification_description='public'
    )
INSERT INTO vdb.related_content
(pk,visibility_classification_id) 
SELECT 'e4327a69-b5d6-4ce3-8e45-b4cae0095282', pk FROM vdb.visibility_classification WHERE classification_description = 'public'
UNION ALL
SELECT '9f7a30e2-efd3-4d51-8584-ce12f1af0b7f', pk FROM vdb.visibility_classification WHERE classification_description = 'public'
UNION ALL
SELECT 'c25038ae-69de-4b0a-9397-fe1d7b8b4529', pk FROM vdb.visibility_classification WHERE classification_description = 'public'
UNION ALL
SELECT '579547d5-4dc8-469a-9bb3-51cd187d4e31', pk FROM vdb.visibility_classification WHERE classification_description = 'public'
UNION ALL
SELECT '20f1f2f9-5475-44b5-b10a-f0d4ec7783c7', pk FROM vdb.visibility_classification WHERE classification_description = 'public'
;


-- create the llm_enrichment table:  
-- data in this table is used to augment prompts sent to an LLM
-- note the use of the vector chunk_embedding
CREATE TABLE IF NOT EXISTS vdb.llm_enrichment(
   pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
   subject_matter string, -- human friendly naive classification
   related_content_id UUID REFERENCES vdb.related_content(pk), -- can be null
   similarity_text string NOT NULL, -- used to create embedding for search
   chunk_embedding VECTOR(768) NOT NULL, -- the whole purpose for this table
   text_chunk string NOT NULL, -- this is the text that augments the prompt to the LLM
   VECTOR INDEX (subject_matter, chunk_embedding vector_cosine_ops) -- non-default cosine nearest neighbor support (default is L2 for KNN)
);

CREATE INDEX IF NOT EXISTS related_content_visibility_idx
ON vdb.related_content (visibility_classification_id);

-- just a simple check for any rows 
SELECT COUNT(*) from vdb.llm_history;


-- just a simple check for one existing llm_response:
SELECT llm_response from vdb.llm_history ORDER BY random() LIMIT 1;