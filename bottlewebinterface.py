from bottle import route, request, run
from prompt_templates import *
from simpleLLM_with_cache import *
from project_utils import *

@route('/hello')
def hello():
    return "Hello World!"

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
    <p><textarea id="large_text" name="user_input" rows="10" cols="50"></textarea></p>
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
                     <p/>
                      <form action="/menu" method="GET">
        <label for="large_text">Go Back To Menu</label>
        <input type="submit" value="Submit">
    </form>
    '''
    
    return page_output

def do_prompt(choice):
    return


if __name__ == '__main__':
    run(host='localhost', port=2020, debug=True)