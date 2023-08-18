import spacy
from pdfminer.high_level import extract_text
import os
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Set the upload folder for the uploaded PDF files
app.config['UPLOAD_FOLDER'] = 'uploads'

models_dir = 'models'  # Base directory for models

# Load all models at startup
def load_models():
    models = {
        'name': spacy.load(os.path.join(models_dir, 'my_name_model')),
        'phone_address': spacy.load(os.path.join(models_dir, 'phone_model_2')),
        'link_github': spacy.load(os.path.join(models_dir, 'linkedin_github_model')),
        'skills': spacy.load(os.path.join(models_dir, 's_model_2')),
        'main': spacy.load(os.path.join(models_dir, 'my_model_3'))
    }
    return models

models = load_models()

def make_entity_dict(doc):
    entities_dict = {}
    for ent in doc.ents:
        entities_dict.setdefault(ent.label_, set()).add(ent.text)
    return entities_dict

def convert_pdf(file_path):
    text = extract_text(file_path)
    return text

def remove_newline(set_of_strings):
    return {string.replace('\n', ' ') for string in set_of_strings}

def get_output(file_path):
    text = convert_pdf(file_path)
    name_dict = make_entity_dict(models['name'](text))
    phone_address_dict = make_entity_dict(models['phone_address'](text))
    del phone_address_dict['Education']
    link_github_dict = make_entity_dict(models['link_github'](text))
    skills_dict = make_entity_dict(models['skills'](text))
    main_dict = make_entity_dict(models['main'](text))
    
    keys_to_check = ['name', 'phone_address', 'link_github', 'skills']
    for key in keys_to_check:
        if key in name_dict or key in phone_address_dict or key in link_github_dict or key in skills_dict:
            main_dict.pop(key, None)

    data = {**name_dict, **phone_address_dict, **link_github_dict, **main_dict, **skills_dict}
    
    empty_keys = [key for key, value in data.items() if value == {None}]
    for key in empty_keys:
        del data[key]
        
    entities_dict = {key: remove_newline(value) for key, value in data.items()}
    
    return entities_dict, text

@app.route('/process_pdf', methods=['GET', 'POST'])
def process_pdf():
    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            return jsonify({"error": "No file provided in the request."}), 400

        pdf_file = request.files['pdf_file']

        if pdf_file.filename == '':
            return jsonify({"error": "No file selected."}), 400

        if pdf_file and allowed_file(pdf_file.filename):
            filename = secure_filename(pdf_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            pdf_file.save(file_path)

            entities_dict, text = get_output(file_path)

            keywords = request.form.get('keywords')
            keywords_list = [keyword.strip() for keyword in keywords.split(',')]
            matching_skills = [i for i in keywords_list if i.lower() in text.lower()]

            os.remove(file_path)

            if not keywords:
                no_keywords_message = "No keywords entered."
                return render_template('result.html', no_keywords_message=no_keywords_message, entities=entities_dict)
            else:
                return render_template('result.html', skills=matching_skills, entities=entities_dict)

    # For GET requests, render the HTML form for manual file upload
    return render_template('upload.html')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf'}

if __name__ == '__main__':
    app.run(debug=True)

