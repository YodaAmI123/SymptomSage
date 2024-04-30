from flask import Flask, request, render_template, send_from_directory, url_for
import os
from flask import redirect,url_for
import vertexai
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.preview.generative_models as generative_models
from PIL import Image
import io
import tensorflow as tf
from tensorflow.keras.models import load_model
import cv2
import numpy as np

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/documentation')
def documentation():
    return render_template('documentation.html')

@app.route('/doctor_login')
def doctor_login():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
      
        
        if name == 'John Doe' and email == 'john@example.com' and password == 'password':
            return redirect(url_for('analyse'))
        else:
            return "Invalid credentials. Please try again."
    
    return render_template('doctor_login.html')



@app.route('/',methods=['GET'])
def index():
    return render_template('index.html')

class PneumoniaDetector:
    def __init__(self, model_path, image_path):
        self.model_path = model_path
        self.image_path = image_path
        self.loaded_model = tf.keras.models.load_model(self.model_path)

    def predict(self):
        img = cv2.imread(self.image_path, cv2.IMREAD_GRAYSCALE)
        resized_img = cv2.resize(img, (150, 150))
        img_array = np.array(resized_img) / 255
        img_array = img_array.reshape(1, 150, 150, 1)

        predictions = self.loaded_model.predict(img_array)
        if predictions[0] > 0.5:
            return "NORMAL"
        else:
            return "PNEUMONIA"

def generate(image_path):
    vertexai.init(project="airy-gate-418807", location="asia-southeast1")
    
    with open(image_path, "rb") as f:
        image = Image.open(f)
        image_data = io.BytesIO()
        image.save(image_data, format="PNG")
        image_data = image_data.getvalue()

    model = GenerativeModel("gemini-1.0-pro-vision-001")
    
    image_part = Part.from_data(
        mime_type="image/png",
        data=image_data,
    )

    text_input = """WRITE 'THIS IS A DETAILED REPORT OF THE SCAN (MAY OR MAYNOT BE ACCURATE)' WRITE A VERY DETAILED REPORT OF THE X-RAY REPORT OF THE SCAN in english. GIVE THE OUTPUT IN THIS FORMAT : {'FINDINGS:'}
    explain in complete medical terms should contain 500 words explaining the compllete medical problem. NOTE--> if the provided image is not an X-Ray GIVE OUTPUT- NOT AN XRAY"""

    generation_config = {
        "temperature": 0.1218484,
        "top_p": 0.5,
        "top_k": 1,
        "max_output_tokens": 2048,
    }

    safety_settings = {
        generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    }

    responses = model.generate_content(
        [image_part, text_input],
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=True,
    )

    result = ""
    for response in responses:
        result += response.text

    return result
@app.route('/patient_login', methods=['GET', 'POST'])
def patient_login():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
      
        
        if name == 'John Doe' and email == 'john@example.com' and password == 'password':
            return redirect(url_for('analyse'))
        else:
            return "Invalid credentials. Please try again."
    
    return render_template('patient_login.html')
@app.route('/analyse', methods=['GET', 'POST'])
def analyse():
    if request.method == 'POST':
        image_file = request.files['image_file']
        image_filename = image_file.filename
        image_path = os.path.join('uploads', image_filename)
        image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

        # Pneumonia detection
        model_path = 'Pneumonia_model.keras'
        detector = PneumoniaDetector(model_path, os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
        prediction = detector.predict()

        # Vertex AI image generation
        generated_report = generate(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
        generated_report=generated_report.replace('**','')
        # Save the report to a file
        report_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{image_filename.split('.')[0]}_report.txt")
        with open(report_path, "w") as f:
            f.write(generated_report)

        patient_name = "John Doe"
        scan_dates = ["2023-04-01", "2023-06-15", "2023-09-20", "2024-01-10", "2024-03-28"]
        

        return render_template('analyse.html', prediction=prediction, generated_report=generated_report, image_path=image_path, patient_name=patient_name, scan_dates=scan_dates)

    return render_template('analyse.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)



if __name__ == '__main__':
    app.run(debug=True)
