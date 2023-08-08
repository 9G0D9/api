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

output_dir='my_model_35'


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

def get_output(nlp, name):
    text = convert_pdf(name)
    doc = nlp(text)
    entities_dict = make_dict(doc, nlp)
    return entities_dict



# Your existing code...

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
            nlp_model = spacy.load(output_dir)
            entities_dict = get_output(nlp_model, file_path)

            # Extract keywords from the form input
            keywords = request.form.get('keywords')
            keywords_list = [keyword.strip() for keyword in keywords.split(',')]

            # Search for keywords in the skills and tools part of the resume
            skills = entities_dict.get('Skills', set())
            tools = entities_dict.get('tools',set())
            matching_skills =[]
            for i in keywords_list :
                for j in skills :
                    if i.lower()==j.lower() :
                        matching_skills.append(i)
                for k in tools :
                    if i.lower()==k.lower():
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
    nlp_model = spacy.load(output_dir)
    app.run(debug=True)
