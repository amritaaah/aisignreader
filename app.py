from flask import Flask, render_template, redirect, send_from_directory, url_for, request, session
import pytesseract
from PIL import Image
import os
import cv2
import numpy as np
from gtts import gTTS
from deep_translator import GoogleTranslator
from flask import send_file
import re





pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

app = Flask(__name__)
app.secret_key = "simple_secret_key"

VALID_USERNAME = "admin"
VALID_PASSWORD = "admin123"

@app.route("/")
def home():
    return render_template("home.html")

def preprocess_adaptive(image_path):
    img = cv2.imread(image_path)
    img = cv2.resize(img, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11, 2
    )
    return thresh


def preprocess_simple(image_path):
    img = cv2.imread(image_path)
    img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    _, thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY)
    return thresh




@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.route("/upload", methods=["POST"])
def upload():
    if "image" not in request.files:
        return render_template("dashboard.html", text=None, audio_file=None, image_file=None)

    file = request.files["image"]

    if file.filename == "":
        return render_template("dashboard.html", text=None, audio_file=None, image_file=None)

    filepath = os.path.join("static", "input.png")
    file.save(filepath)

    img1 = preprocess_adaptive(filepath)
    img2 = preprocess_simple(filepath)

    config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ'

    text1 = pytesseract.image_to_string(img1, config=config)
    text2 = pytesseract.image_to_string(img2, config=config)

    def clean_text(t):
        t = t.upper()
        t = re.sub(r'[^A-Z ]', ' ', t)
        t = re.sub(r'\s+', ' ', t).strip()
        return t

    text1 = clean_text(text1)
    text2 = clean_text(text2)

    print("Adaptive OCR:", text1)
    print("Simple OCR:", text2)

    known_words = ["SCHOOL", "AHEAD", "HOSPITAL", "STOP", "DANGER", "POLICE", "STATION"]

    def score(text):
        count = 0
        for word in known_words:
            if word in text:
                count += 1
        return count

    score1 = score(text1)
    score2 = score(text2)

    final_text = text1 if score1 >= score2 else text2
    print("Final Selected:", final_text)

    text = final_text

    # Insert spacing around known words
    for word in known_words:
        text = text.replace(word, f" {word} ")

    text = re.sub(r'\s+', ' ', text).strip()

    # 🔥 Strong filtering: keep ONLY valid sign words
    words = text.split()
    words = [w for w in words if w in known_words]
    text = " ".join(words)

    print("CLEANED TEXT:", text)

    return render_template(
        "dashboard.html",
        text=text,
        audio_file=None,
        image_file="input.png"
    )



@app.route("/read", methods=["POST"])
def read_aloud():
    text = request.form.get("text")
    image_file = request.form.get("image_file")


    if not text:
        return render_template("dashboard.html", text=None, audio_file=None, image_file=image_file)
    
    manual_dict = {
    "school": "സ്കൂൾ",
    "hospital": "ആശുപത്രി",
    "ahead": "മുന്നിൽ",
    "police": "പോലീസ്",
    "stop": "നിർത്തുക",
    "danger": "അപായം"
    } 


    # Translate English to Malayalam
    words = text.lower().split()
    translated_words = []

    for word in words:
     if word in manual_dict:
        translated_words.append(manual_dict[word])
     else:
        translated_words.append(
            GoogleTranslator(source='auto', target='ml').translate(word)
        )

    translated_text = " ".join(translated_words)



    # Convert Malayalam text to speech
    tts = gTTS(text=translated_text, lang='ml')
    audio_path = "static/output.mp3"
    tts.save(audio_path)


    return render_template(
        "dashboard.html",
        text=text,
        audio_file="output.mp3",
        image_file=image_file
    )



if __name__ == '__main__':
    app.run(debug=True)

