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
    prompts= ''
    for key in TEMPLATE_MAP:
        prompts+=key
        prompts+='  |  '
    html=f'''
<h2><p>Choose a prompt_template or RAG</p>
<p>Confirm if you want to save the resulting response, then enter your question or prompt to be processed...</p></h2>
<h1>{prompts}</h1>
<form action="/menu" method="post">
    <p>
    prompt_option: <input name="choice" type="text" value="base"/>
    </p>
    <p>
    save_llm_response: <input name="save" type="text" value="False" />
    </p>
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
    save = request.forms.save
    page_output = f''' you selected: {prompt_template} with <p>{user_input}</p> and <p>{save}'''
    embed = create_embedding(user_input)
    config_dict=configure_temperature_and_template(prompt_template)
    template_func=config_dict.get("template_func")
    start_time=time.perf_counter()
    llm_interrupt_time=0
    response_dict = query_using_vector_similarity(embed,star_rating_target,template_func.__name__)
    
    llm_response = f"Similarity_Percentage = {response_dict.get("similarity_percent")}<p/>"+str(response_dict.get("cached_response"))
    if None==response_dict.get("pk"):
        llm_interrupt_time=time.perf_counter()
        llm_response = ask_llm(user_input,config_dict) 
        llm_interrupt_time=time.perf_counter()-llm_interrupt_time
        if save=="True":
            #print('before DB insert...')
            pk = insert_llm_prompt_response(embed,user_input,llm_response,template_func.__name__)
        duration=(time.perf_counter()-(start_time+llm_interrupt_time))*1
        print(f'\t{uparrows}\tElapsed Time spent querying database was: {duration} seconds\n')
        print(f'\t{uparrows}\tElapsed Time spent querying LLM was: {llm_interrupt_time} seconds\n')
    page_output+=f'''<p><h3><hr/>Here is the response from your prompt: <p/><hr/><p/>{llm_response.replace('.', '.<br/>')}</h3></p>
                     <p>
                     <h4>
                     <ul>
                        <li>Elapsed Time spent querying database was: {duration} seconds</li>
                        <li>Elapsed Time spent querying LLM was: {llm_interrupt_time} seconds</li>
                     </ul>
                     </h4>
                     </p>
                     <p/>{main_menu_form}
    '''
    
    return page_output

def do_prompt(choice):
    return


if __name__ == '__main__':
    run(host='localhost', port=2020, debug=True)