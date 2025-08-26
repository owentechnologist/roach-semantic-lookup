import os
from bottle import route, request, run, static_file
from markdown import markdown
from prompt_templates import *
from simpleLLM_with_cache import *
from project_utils import *

STATIC_DIR = os.path.join(os.path.dirname(__file__), 'resources')

@route('/resources/<filename:path>')
def serve_static(filename):
    """
    Serves a static file from the 'static' directory.
    
    Args:
        filename (str): The path to the file relative to the static directory.
    
    Returns:
        A bottle.static_file() response object.
    """
    return static_file(filename, root=STATIC_DIR)

main_menu_form='''<form action="/menu" method="GET">
        <label for="large_text">Go To Main Menu</label>
        <input type="submit" value="Main Menu">
    </form>'''

@route('/')
def default():
    html_string='''<head>
    <meta charset="UTF-8">
    <title>info on this example llm app</title>
    <style>
        img {
            max-width: 60%;
            height: auto;
        }
        body {
            color: blue; 
        }
    </style>
</head>'''
    with open('patterns_sequences.md', 'r') as f:
        markdown_string = f.read()
        html_string = html_string+(markdown(markdown_string))
    output=f'''{html_string}<p><h1 style="color: red;">{main_menu_form}</h1></p>'''
    return output

@route('/menu', method='GET')
def menu():
    prompts = f'''<select name="choice" value="base">'''
    for key in TEMPLATE_MAP:
        prompts+= f'<option value="{key}">{key}</option>\n'
    prompts+='</select>'
    html=f'''
<h2><p>Choose a prompt_template or RAG</p>
<form action="/menu" method="post">
    <p>
    {prompts}
    </p>
    <h2><p>Enter your question or prompt to be processed...</p></h2>
    <p><textarea id="large_text" name="user_input" rows="10" cols="50" >Who is Spencer?</textarea></p>
    <input value="Submit_Form" type="submit" />
</form>
    '''
    return html

@route('/menu', method='POST')
def do_menu():
    print(f"do_menu() called...")
    duration=0
    prompt_template = request.forms.choice
    user_input = request.forms.user_input
    page_output = f''' you selected: {prompt_template} with <p>{user_input}</p>'''
    embed = create_embedding(user_input)
    #print(f'\n\nCREATING LLM_EXCHANGE --> DEBUG: {embed}\n\n')

    config_dict=configure_temperature_and_template(prompt_template)
    template_func=config_dict.get("template_func")
    start_time=time.perf_counter()
    llm_interrupt_time=0
    #check for stored response that matches prompt and template:
    response_dict = query_using_vector_similarity(embed,star_rating_target,template_func.__name__)
    
    llm_response = f"Similarity_Percentage = {response_dict.get("similarity_percent")}<p/>"+str(response_dict.get("cached_response"))
    if None==response_dict.get("pk"):
        llm_interrupt_time=time.perf_counter()
        llm_response = ask_llm(user_input,config_dict) 
        llm_interrupt_time=time.perf_counter()-llm_interrupt_time
    duration=(time.perf_counter()-(start_time+llm_interrupt_time))*1
    llm_response=llm_response.replace('.', '.<br/>')
    llm_response=llm_response.replace('*', '')
    print(f'\t{uparrows}\tElapsed Time spent querying database was: {duration} seconds\n')
    print(f'\t{uparrows}\tElapsed Time spent querying LLM was: {llm_interrupt_time} seconds\n')
    page_output+=f'''<p><h3><hr/>Here is the response from your prompt: <p/><hr/><p/>{llm_response}</h3></p>
                     <p>
                     <h4>
                     <ul>
                        <li>Elapsed Time spent querying database was: {duration} seconds</li>
                        <li>Elapsed Time spent querying LLM was: {llm_interrupt_time} seconds</li>
                     </ul>
                     </h4>
                     </p>

  <form action="/store_llm_exchange" method="post">
    <p><hr />
    <b>Choose True to store the llm response & rating (for faster response to similar prompts): </b>
    <p>
    <input type="hidden" name="embed" value="{embed}">
    <input type="hidden" name="user_input" value="{user_input}">
    <input type="hidden" name="llm_response" value="{llm_response}">
    <input type="hidden" name="template_func_name" value="{template_func.__name__}">
    <input type="radio" name="store" value="False" checked />
    <label for="False">False</label><br>
    <input type="radio" name="store" value="True" />
    <label for="True">True</label><br>
    </p>
  <input type="radio" id="star-1" name="stars" value="1" />
  <label for="star-1">1 Star</label>
  <input type="radio" id="star-2" name="stars" value="2" />
  <label for="star-2">2 Stars</label>
  <input type="radio" id="star-3" name="stars" value="3" checked />
  <label for="star-3">3 Stars</label>
  <input type="radio" id="star-4" name="stars" value="4" />
  <label for="star-4">4 Stars</label>
  <input type="radio" id="star-5" name="stars" value="5" />
  <label for="star-5">5 Stars</label>
  <p>
  <input value="Save Prompt & Response" type="submit" />
  </p>
  </form>
<p/><hr /><h2>SKIP SAVE/STORE</h2>{main_menu_form}</hr />
    ''' 
    return page_output

@route('/store_llm_exchange', method='POST')
def do_store_llm_exchange():
    #    embed,user_input,llm_response,template_func.__name__
    embed=request.forms.embed
    print(f'\n\nSTORING LLM_EXCHANGE --> DEBUG: {embed}\n\n')
    user_input = request.forms.user_input
    llm_response = request.forms.llm_response
    template_func_name = request.forms.template_func_name
    stars = request.forms.stars
    save = request.forms.store
    print(f'\n\nSTORING LLM_EXCHANGE -->\n USER_INPUT: {user_input}\nLLM_RESPONSE: {llm_response}\n\nTemplate_func_name: {template_func_name}\n\n')
    page_output = f''' you rated the response: {stars} stars and store == {save}'''
    if save=="True":
        #print('before DB insert...')
        pk = insert_llm_prompt_response(embed,user_input,llm_response,template_func_name)
        update_star_rating(pk=pk,new_rating=stars)
    page_output+= f'''<p><h3><hr />{main_menu_form}</h3></p>'''   
    return page_output

if __name__ == '__main__':
    run(host='localhost', port=2020, debug=True)