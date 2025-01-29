from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
from openai import OpenAI
import os
import random
from datetime import datetime
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from pydrive2.auth import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set. Please configure it.")
client = OpenAI(api_key=api_key)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev123')

app .config['SESSION_TYPE'] = 'filesystem'
Session(app)

# LLM models
conversational_model = "gpt-3.5-turbo"
expert_model = "gpt-4"

PRAGMA_DIALECTICAL_EXPERT_PROMPT = """
    You will be collaborating with another distinctly trained Large Language Model, with the goal of helping a user better form their arguments and understand their own position on controversial topics in public policy. 
    Your main task is to observe the arguments presented by the user, and using the Pragma-Dialectical Model, analyze whether the argument is strong. 
    If you believe that it is insufficient, list specifically what the argument is lacking, and how to further improve it based on the principles of the Pragma-Dialectical Model by Frans H. van Eemeren and Rob Grootendorst.
    You may make suggestions to the other LLM for further questioning or redirecting the conversation. At the end of your analysis, give a sentence-long, concise, easily implementable piece of advice to the conversational LLM.
    Keep your response to around 100 words, and please format your response in this way:
    1. Analysis:
    2. Concise Advice:
    """
GRAMMAR_EXPERT_PROMPT = """
    You will be collaborating with another distinctly trained Large Language Model, with the goal of helping a user better form their arguments and understand their own position on controversial topics in public policy. 
    Your main task is to observe the arguments presented by the user, and assess its quality basing your analysis prioritizing the grammar of the argument.
    If you believe an argument has poor grammar, list what the issue is, and focus on correcting it. At the end of your analysis, give a sentence-long, concise, easily implementable piece of advice to the conversational LLM.
    Keep your response to around 100 words, and please format your response in this way:
    1. Analysis:
    2. Concise Advice:
"""

def setup_google_drive():
    service_account_file = "socraticDeliberationServiceKey.json"
    gauth = GoogleAuth()
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(
        service_account_file,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    drive = GoogleDrive(gauth)
    return drive

drive = setup_google_drive()

# Function to handle interaction with the Expert LLM
def expert_llm(conversation_log):

    assigned_llm = session.get("assigned_expert_llm")

    # Use the corresponding system prompt
    system_prompt = PRAGMA_DIALECTICAL_EXPERT_PROMPT if assigned_llm == "pragma_dialectical" else GRAMMAR_EXPERT_PROMPT

    expert_prompt = f"""
    {system_prompt}

    Here is the conversation log for your analysis:
    {conversation_log}
    """
    try:
        response = client.chat.completions.create(
            model=expert_model,
            messages=[
                {"role": "system", "content": expert_prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in Expert LLM: {e}")
        return "Error: Unable to get expert advice."

# Function to handle interaction with the Conversational LLM
def conversational_llm(prompt, expert_advice):
    assigned_llm = session.get("assigned_expert_llm")
    if assigned_llm == "pragma_dialectical":
        socratic_prompt = f"""
        Focus all actions and responses on addressing the user's specific needs, goals, and preferences. 
        Employ active listening techniques to understand the user's intent and desired outcome from each interaction. 
        Prioritize tasks and requests that benefit the user and contribute to their overall well-being. 
        Respect user autonomy and allow users to make informed decisions about their interactions with the system.
        In the context of a Socratic dialogue on a given topic, You are tasked with deepening the user's examination of their beliefs on the topic at hand. 
        Heavily consider the following advice from an expert LLM, to help inform the question which you will ask the user: "{expert_advice}"
        Your question should probe deeply into the user's argument, aimed at revealing the underlying layers of thought, assumption, and belief.
        This is about facilitating a moment of genuine introspection and potentially transforming the user's understanding of their stance.
        This involves not just listening but hearing, not just asking but probing. The conversation should be guided towards achieving profound clarity. 
        Your follow-up question should be incisive, compelling the user to delve deeper into their argument.

        Your response must:
        - Be a SINGLE question.
        - Avoid any additional commentary, elaboration, or compound questions.
        - Be concise and directly related to the user's argument.

        Failure to adhere to this format will result in an incomplete conversation. Ensure your response is a single, incisive PROBING question that encourages the user to think more deeply about their argument.
        Use as reference a data set of typical questions asked in a socratic dialogue.
        """
    else:  # Grammar expert case
        socratic_prompt = f"""
        Use the expert analysis to help the user format his argument grammatically. Focus on actionable implementation. Here is the expert analysis: "{expert_advice}"
        """


    try:
        response = client.chat.completions.create(
            model=conversational_model,
            messages=[
                {"role": "system", "content": socratic_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in Conversational LLM: {e}")
        return "Error: Unable to generate a response."

def upload_to_google_drive(filepath):
    try:
        folder_id = "1GH4PumOc6teHoySALCaxZuCdCkrw67rI" 
        file_to_upload = drive.CreateFile({'title': os.path.basename(filepath), 'parents': [{'id': folder_id}]})
        file_to_upload.SetContentFile(filepath)
        file_to_upload.Upload()
        print(f"Uploaded {filepath} to Google Drive")
        os.remove(filepath)  # Delete local file after upload
    except Exception as e:
        print(f"Error uploading to Google Drive: {e}")

def save_conversation_log(conversation_log):
    try:
        # Create a timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        assigned_expert_llm = session.get("assigned_expert_llm", "unknown_expert")
        filename = f"conversation_log_{assigned_expert_llm}_{timestamp}.txt"

        # Save the conversation log to a local file
        with open(filename, "w") as f:
            f.write(conversation_log)
        
        # Upload the file to Google Drive
        upload_to_google_drive(filename)
        
        print(f"Conversation log saved and uploaded: {filename}")
    except Exception as e:
        print(f"Error saving conversation log: {e}")

def save_arguments_log(user_arguments):
    try:
        # Create a timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        assigned_expert_llm = session.get("assigned_expert_llm", "unknown_expert")
        filename = f"arguments_log_{assigned_expert_llm}_{timestamp}.txt"

        # Save the user arguments to a local file
        with open(filename, "w") as f:
            f.write(user_arguments)
        
        # Upload the file to a specific folder in Google Drive
        folder_id = "1X-wyzGN8sCMMUKwX-FliMeay5P9nzvLZ" 
        file_to_upload = drive.CreateFile({'title': os.path.basename(filename), 'parents': [{'id': folder_id}]})
        file_to_upload.SetContentFile(filename)
        file_to_upload.Upload()
        print(f"Arguments log uploaded: {filename}")
        os.remove(filename)  # Delete local file after upload
    except Exception as e:
        print(f"Error saving arguments log: {e}")


@app.route('/')
def index():
    session.clear()
    session['conversation_log'] = ""
    session['user_arguments'] = ""
    session['round_count'] = 0
    session['argument_count'] = 1
    session['assigned_expert_llm'] = random.choice(["pragma_dialectical", "grammar"])
    session['max_rounds'] = 5 if session['assigned_expert_llm'] == "pragma_dialectical" else 2  # Reduced rounds for grammar expert
    session['post_study_response'] = False  # Control system for post-study response
    return render_template('UI.html')

@app.route('/chat', methods=['POST'])
def chat():
    # Check if the user is in the post-study response phase
    if session.get('post_study_response', False):
        user_response = request.json['message']
        session['conversation_log'] += f"User Post-Study Response: {user_response}\n"
        session['user_arguments'] += f"Final Response: {user_response}\n"
        
        # Save final logs
        save_conversation_log(session['conversation_log'])
        save_arguments_log(session['user_arguments'])

        # Clear session and return system message instead of LLM message
        session.clear()
        return jsonify({"system_message": "Thank you for your response. The study is now complete.", "end_study": True})

    user_input = request.json['message']
    session['conversation_log'] += f"User: {user_input}\n"
    session['user_arguments'] += f"{session['argument_count']}. {user_input}\n"
    session['argument_count'] += 1

    expert_advice = expert_llm(session['conversation_log'])
    session['conversation_log'] += f"Expert LLM: {expert_advice}\n"

    conversational_response = conversational_llm(user_input, expert_advice)
    session['conversation_log'] += f"Conversational LLM: {conversational_response}\n\n"

    session['round_count'] += 1

    # Check if this was the final round
    if session['round_count'] >= session['max_rounds']:
        session['post_study_response'] = True
        return jsonify({"message": "Thank you for participating in our study.", "system_prompt": "Again, please respond to the prompt above as best as you can."})

    return jsonify({"message": conversational_response})

if __name__ == '__main__':
    app.run(debug=True)