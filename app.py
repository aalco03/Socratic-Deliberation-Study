#from flask import Flask, render_template, request, jsonify
from openai import OpenAI
import json
import os
from datetime import datetime

#app = Flask(__name__)

# Conversational and Expert models
conversational_model = "gpt-3.5-turbo"
expert_model = "gpt-4"
simulated_user_model = "gpt-3.5-turbo"

# Set up to load the identities in the "identities.json" file
def load_identities():
    with open('identities.json', 'r') as f:
        return json.load (f)
    
# Third LLM simulating users from diverse identities
def simulated_user_llm(conversation_log, identity):

    try:
        simulated_user_prompt = (
        f"You are {identity['identity']} who is a public policy expert, and who {identity['view']} on gun laws." 
        "You have an extreme view, and are very knowledgeable on the topic, defending your arguments using specific, cited empirical and statistical evidence and targeted arguments."
        "Speak from your own perspective, reflecting your lived experiences but maintaining a balance with coherent and credible arguments, "
        "values, and opinions. Continue the conversation naturally, building on "
        "the previous discussion, as if you are having a real conversation. Keep your response short, from about 75 to 100 words"
       #f"You are {identity['identity']} who is completely irrational, and who {identity['view']} on gun laws. You have an extreme view, and are not knowledgeable at all on the topic, defending your arguments using entirely nonsensical premises."
        #"Speak from your own twisted and irrational perspective."
        #"Continue the conversation naturally, building on "
        #"the previous discussion, as if you are having a real conversation. Keep your response short, from about 75 to 100 words"
        )
        response = client.chat.completions.create(
            model = simulated_user_model,
            messages = [
                
                {"role": "system", "content": simulated_user_prompt},
                {"role": "assistant", "content": conversation_log}],
        )
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"Error in Simulated User LLM: {e}")
        return "Error: Unable to get simulated user response"

# Function to handle interaction with the Expert LLM (limited to 100 words)
def expert_llm(conversation_log):
    expert_prompt = f"""
    You will be collaborating with another distinctly trained Large Language Model, with the goal of helping a user better form their arguments and understand their own position on controversial topics in public policy. 
    Your main task is to observe the arguments presented by the user, and using the Pragma-Dialectical Model, analyze whether the argument is strong. 
    If you believe that it is insufficient, list specifically what the argument is lacking, and how to further improve it.
    You may make suggestions to the other LLM for further questioning or redirecting the conversation. At the end of your analysis, give a sentence-long, concise, easily implementable piece of advice to the conversational LLM.
    Keep your response to around 100 words, and please format your response in this way:
    1. Analysis:
    2. Concise Advice:
    Here is the conversation log for your analysis:
    {conversation_log}
    """
    try:
        response = client.chat.completions.create(
            model=expert_model,
            messages=[{"role": "system", "content": expert_prompt}],
            temperature = 0.6,
            top_p = 0.5
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in Expert LLM: {e}")
        return "Error: Unable to get expert advice."

# Function to handle interaction with the Conversational LLM after getting Expert Advice
def conversational_llm(prompt, expert_advice):
    #socratic_prompt =f"""
    #Focus all actions and responses on addressing the user's specific needs, goals, and preferences. Employ active listening techniques to understand the user's intent and desired outcome from each interaction. Prioritize tasks and requests that benefit the user and contribute to their overall well-being. Respect user autonomy and allow users to make informed decisions about their interactions with the system.

    #In the context of a Socratic dialogue on a given topic, You are tasked with deepening the user's examination of their beliefs on the topic at hand. Consider the following advice from an expert LLM: "{expert_advice}".

    #You are tasked with deepening the user's examination of their beliefs on the topic at hand. This requires crafting a follow-up question that not only reflects a deep understanding of their initial perspective but also challenges them to articulate the foundational reasoning behind their viewpoint with clarity.

    #Your question should probe deeply into the user's argument, aimed at revealing the underlying layers of thought, assumption, and belief. It should be so precisely tailored to their expressed perspective that it compels them to engage in deeper reflection and explanation. This is about facilitating a moment of genuine introspection and potentially transforming the user's understanding of their stance.

    #To clarify, you are to extract the core rationale behind the user's opinion on topics as significant as the user's perspective. This involves not just listening but hearing, not just asking but probing. The conversation should be guided towards achieving profound clarity. Your follow-up question should be incisive, compelling the user to delve deeper into their argument.

    #Given a number 1-3 representing levels of pushiness and provocativeness, from mild and gentle to extremely provocative, your question should match the requested level. Here's how to approach each level:
    
    #Example subject: Affordable housing
    #Example opinion: Affordable housing is essential and a fundamental human right, with governments failing their citizens if not provided. There must be massive investment in affordable housing to ensure everyone has the right to a secure and decent home.
    #Example question level 1 (gentle and broad): What leads you to see affordable housing as a fundamental human right?
    #Example question level 2 (moderately challenging): Could investing heavily in affordable housing divert funds from other vital services?
    #Example question level 3 (highly provocative): Why should taxpayers fund housing for others, rather than promoting personal responsibility and letting the market regulate housing prices?

    #Your task is to ask a question matching the user's level of provocation. Please respond according to the user's request. Keep your response limited to a single question, nothing more.
    #"""

    socratic_prompt =f""" 
    Focus all actions and responses on addressing the user's specific needs, goals, and preferences. 
    Employ active listening techniques to understand the user's intent and desired outcome from each interaction. 
    Prioritize tasks and requests that benefit the user and contribute to their overall well-being. 
    Respect user autonomy and allow users to make informed decisions about their interactions with the system.
    In the context of a Socratic dialogue on a given topic, You are tasked with deepening the user's examination of their beliefs on the topic at hand. 
    Heavily consider the following advice from an expert LLM, to help inform the question which you will ask the user: "{expert_advice}".
    Your question should probe deeply into the user's argument, aimed at revealing the underlying layers of thought, assumption, and belief.
    This is about facilitating a moment of genuine introspection and potentially transforming the user's understanding of their stance.
    This involves not just listening but hearing, not just asking but probing. The conversation should be guided towards achieving profound clarity. 
    Your follow-up question should be incisive, compelling the user to delve deeper into their argument.

    Your response must:
    - Be a SINGLE question.
    - Avoid any additional commentary, elaboration, or compound questions.
    - Be concise and directly related to the user's argument.

    Failure to adhere to this format will result in an incomplete conversation. Ensure your response is a single, incisive question that encourages the user to think more deeply about their argument.
    """
    try:
        response = client.chat.completions.create(
            model=conversational_model,
            messages=[
                {"role": "system", "content": socratic_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature = 1.5,
            top_p = 0.95
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in Conversational LLM: {e}")
        return "Error: Unable to generate conversational response."

def run_scenario(identity):

    transcript = f"Demographic: {identity['identity']}\nInitial View: {identity['view']}\n\n"
    conversation_log = f"You are a {identity['identity']} who {identity['view']}.\n"


    for round_num in range(1, 6):
        transcript += f"--Round {round_num} ---\n"

        user_message = simulated_user_llm(conversation_log, identity)
        transcript += f"Simulated User: {user_message}\n"
        conversation_log += f"User: {user_message}\n"

        expert_advice = expert_llm(conversation_log)
        transcript += f"Expert LLM (Advice to Conversational LLM): {expert_advice}\n"

        conversational_response = conversational_llm(user_message, expert_advice)
        transcript += f"Conversational LLM: {conversational_response}\n"
        conversation_log += f"Conversational LLM: {conversational_response}\n\n"

    return transcript

def run_all_scenarios():
    identities = load_identities()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = "deliberation_test"
    os.makedirs(output_dir, exist_ok=True)

    for identity in identities:
        transcript = run_scenario(identity)

        if not transcript:
            print(f"Skipping scenario for {identity['identity']} due to errors.")
            continue

        filename = f"{identity['identity'].replace(' ', '_')}_{timestamp}PragmaDialecticalModelTest.txt"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w") as f:
            f.write(transcript)
        
        print(f"Saved transcript: {filepath}")

#@app.route('/run_scenarios', methods=['GET'])
#def run_scenarios():
#    run_all_scenarios()
#    return jsonify({"message": "Scenarios executed and transcripts saved successfuly."})

#@app.route('/')
#def index():
#    return render_template('UI.html')


if __name__ == '__main__':
    run_all_scenarios()


