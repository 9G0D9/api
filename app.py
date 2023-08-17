import spacy
from spacy.training.example import Example
import random
import json
import pandas as pd
from pdfminer.high_level import extract_text
import os
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Set the upload folder for the uploaded PDF files
app.config['UPLOAD_FOLDER'] = 'uploads'

name_dir='models//my_name_model'
phone_address_dir='models//phone_model_2'
link_github_dir='models//linkedin_github_model'
main_dir='models//my_model_3'


def make_dict(doc, nlp):
    # Get all possible entity labels from the model
    all_entity_labels = nlp.get_pipe("ner").labels

    # Initialize a dictionary to store entities for each label as sets
    entities_dict = {label: set() for label in all_entity_labels}

    # Extract entities and group them by label
    for ent in doc.ents:
        entities_dict[ent.label_].add(ent.text)

    # Convert empty sets to sets containing None for all labels
    for label in entities_dict:
        if not entities_dict[label]:
            entities_dict[label].add(None)
            
    return entities_dict



def convert_pdf(name):
    text=extract_text(name)
    return text

def remove_newline(set_of_strings):
    return {string.replace('\n', ' ') for string in set_of_strings}

def get_output(name_model,phone_address_model,link_github_model,main_model, name):
    text = convert_pdf(name)
    name_dict = make_dict(name_model(text), name_model)
    phone_address_dict = make_dict(phone_address_model(text), phone_address_model)
    del phone_address_dict['Education']
    link_github_dict = make_dict(link_github_model(text), link_github_model)
    main_dict = make_dict(main_model(text), main_model)
    #remove alredy existing entities from main_dict
    l=[]
    for i in main_dict.keys():
        if (i in name_dict.keys() or i in phone_address_dict.keys() or i in link_github_dict.keys()):
            l.append(i)
    for j in l:
        del main_dict[j]
        
    
    data={**name_dict , **phone_address_dict , **link_github_dict , **main_dict}
    
    #remove empty values
    l2=[]
    for key in data.keys():
        if data[key]=={None}:
            l2.append(key)
    
    for key in l2 :
        del data[key]
        
    #remove '\n
    entities_dict = {key: remove_newline(value) for key, value in data.items()}
    
    return entities_dict,text



@app.route('/process_pdf', methods=['GET', 'POST'])
def process_pdf():
    if request.method == 'POST':
        # Check if the request contains a file with the key 'pdf_file'
        if 'pdf_file' not in request.files:
            return jsonify({"error": "No file provided in the request."}), 400

        pdf_file = request.files['pdf_file']

        if pdf_file.filename == '':
            return jsonify({"error": "No file selected."}), 400

        if pdf_file and allowed_file(pdf_file.filename):
            filename = secure_filename(pdf_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            pdf_file.save(file_path)
            name_model = spacy.load(name_dir)
            phone_address_model = spacy.load(phone_address_dir)
            link_github_model = spacy.load(link_github_dir)
            main_model = spacy.load(main_dir)

            entities_dict, text = get_output(name_model,phone_address_model,link_github_model,main_model, file_path)

            # Extract keywords from the form input
            keywords = request.form.get('keywords')
            keywords_list = [keyword.strip() for keyword in keywords.split(',')]

            # Search for keywords in the resume
            
            matching_skills =[]
            
            for i in keywords_list :
                if i.lower() in text.lower() and i.lower() not in matching_skills :
                    matching_skills.append(i)

            os.remove(file_path)
            
            if not keywords:
                no_keywords_message = "No keywords entered."
                return render_template('result.html', no_keywords_message=no_keywords_message , entities=entities_dict)
            else:
                # Render the result.html template with the matching skills as context data
                return render_template('result.html', skills=matching_skills , entities=entities_dict)

            
            

    # For GET requests, render the HTML form for manual file upload
    return render_template('upload.html')





def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf'}

if __name__ == '__main__':
    
    app.run(debug=True)
