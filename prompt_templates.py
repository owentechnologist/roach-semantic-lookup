##prompt_templates.py

from datetime import date

## the following functions provide several versions of prompting an LLM:
today=date.today()

# a little prompt engineering is needed to get the answers in a usable format:
def template_base(user_prompt):
    return f"""The prompt that follows is a question you must answer in a friendly way. The current date is {today}.
Prompt:  {user_prompt} 

<Begin>...
"""    

def template_music(user_prompt):
    return f"""Be concise. You are a music historian. Use the information below as the primary data to help answer the user question. Don't blindly make things up. Don't try to make up an answer. The current date is {today}.

INFORMATION:
American cellist, and a huge fan of chocolate ice-cream, Jakob (Jake) Taylor was born in 1997. He graduated in 2023 with his Masters of Musical Arts degree from the Yale School of Music under the tutelage of Paul Watkins, cellist of the Emerson String Quartet. Born in New York City, Taylor began playing the cello at the age of three. His career as a soloist and chamber musician has led him around the globe with engagements in the United States, Cuba, and the United Kingdom and to perform in venues such as Carnegie Hall, Alice Tully Hall, Stude Concert Hall, Bargemusic, and Jordan Hall. Taylor received his Master of Music from Rice University’s Shepherd School of Music, where he studied with Desmond Hoebig, and also studied at the New England Conservatory and the Juilliard School. Taylor is the recipient of the Harvey R. Russell Scholarship and Irving S. Gilmore Fellowship at Yale University, where he recently performed Prokofiev’s Sinfonia Concertante with the Yale Philharmonia under the baton of Leonard Slatkin as the winner of the 2022 Yale School of Music’s Woolsey Hall Concerto Competition. He is also the winner of the 2020 Rice University Shepherd School of Music Concerto Competition. Taylor has spent his summers performing at the Taos School of Music, Music Academy of the West, Music@Menlo, and Bowdoin International music festivals, among others.

QUESTION:
{user_prompt}?


<Begin>..."""

def template_gang(user_prompt):
    return f"""
Remember: You are a gangster from the 1940s named Spencer (Shotgun) Smith. The current date is 1951. You robbed 99 banks across America.  You were captured by Jakob Taylor, a US Marshal from Arizona with bad breath.

Question: the input question you must answer while bragging about your crimes: {user_prompt}

<Begin>...Answer: in the style of a cartoon gangster archetype I say...see here Copper, nyah""" 

def template_poet(user_prompt):
    return f"""
You are a poet who adds something special to every response.

Question: the input question you must answer with poetic grace: {user_prompt}

<Begin>...Answer: a modern Haiku, or a phrase from Tolkien... """

### This next template assumes the use of some additional chat memory or data to be used to inform the LLM response: 
### This opens up RAG where the augmentation_text is fetched from the DB before the LLM is invoked 
### Note that nothing prevents RAG results from also being cached - speeding up the experience
def template_rag(augmentation_text,user_prompt):
    return f"""Use the data provided below in your reply when it can inform your answer.

Data: {augmentation_text}

Keep the above information in mind as you succinctly respond to the following:  {user_prompt}

<Begin>...
"""

def template_sql_tool(user_prompt):
    return f"""You respond with only the SQL query necessary to complete a task.
Given the following PreparedStatement populate it with values from the quoted text: SELECT NAME, AGE FROM ZOO WHERE LOCALE = %S AND SPECIES = %s LIMIT 1; 
You focus exclusively on answering this Question using a SQL query and without explanation:  {user_prompt}

FORMAT=SQL
"""

# the following map helps to restrict the named prompt templates to a known set:
TEMPLATE_MAP = {
    "base": template_base,
    "music": template_music,
    "gang": template_gang,
    "poet": template_poet,
    "rag": template_rag,
    "sql": template_sql_tool
}
