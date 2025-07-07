# roach-semantic-lookup
This example calls an LLM, stores the LLM response as text, along with both a vector embedding of the prompt and the text of the prompt used. The datastore used is CRDB.  The example also showcases searching for a prompt using Vector Search in order to avoid repeated calls to the LLM.  This is known as semantic caching.
