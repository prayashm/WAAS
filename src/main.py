from distutils.log import error
import whisper
from flask import Flask
from flask import request
from flask import render_template
import tempfile
import logging

from src.utils import generate_srt, generate_vtt

app = Flask(__name__)

DEFAULT_MODEL = "tiny"
DEFAULT_TASK = "transcribe"

def is_invalid_params (req):
    requestedModel = req.args.get("model", DEFAULT_MODEL)
    language = req.args.get("language")
    task = req.args.get("task", DEFAULT_TASK)

    # Check if model is available
    if requestedModel not in whisper.available_models():
        return "Model not available", 400
    
    # when language is set, check if it is in the whisper.tokenizer.LANGUAGES list
    if language is not None:
        if language not in whisper.tokenizer.LANGUAGES:
            return "Language not supported", 400

    # Check if task is either translate or transcribe
    if task not in ["translate", "transcribe"]:
        return "Task not supported", 400
    
    # Check if the request contains a file
    if "file" not in req.files:
        return "No file provided", 400
    
    file = req.files['file']

    # check if the file is supported
    filename = file.filename
    if not filename.endswith(".mp3") and not filename.endswith(".mp4"):
        return "Filetype is not accepted", 415
    
    return False

@app.route("/",methods=['GET'])
def index():
    return render_template("index.html")

@app.route("/v1/transcribe", methods=['POST'])
def transcribe():
    tempFile = tempfile.NamedTemporaryFile()
    try:
        # Get variables from request
        requestedModel = request.args.get("model", DEFAULT_MODEL)
        task = request.args.get("task", DEFAULT_TASK)
        language = request.args.get("language")

        request_is_invalid = is_invalid_params(request)
        if request_is_invalid:
            return request_is_invalid
            
        # Download the file
        file = request.files['file']
        tempFile.write(file.read())

        model = whisper.load_model(requestedModel)
        result = model.transcribe(tempFile.name, language=language, task=task)

        if request.accept_mimetypes['text/plain']:
            return result["text"]
        if request.accept_mimetypes['application/json']:
            return result        
        if request.accept_mimetypes['text/vtt']:
            return generate_vtt(result["segments"]), 200, {'Content-Type': 'text/vtt', 'Content-Disposition': 'attachment; filename=transcription.vtt'}
        
        return generate_srt(result["segments"]), 200, {'Content-Type': 'text/plain', 'Content-Disposition': 'attachment; filename=transcription.srt'}
    except Exception as e:
        logging.exception(e)
        return 500
    finally:
        tempFile.close()

@app.route("/v1/transcribe/options", methods=['GET'])
def options():
    return {
        "models": whisper.available_models(),
        "languages": whisper.tokenizer.LANGUAGES,
        "tasks": ["translate", "transcribe"]
    }

@app.route("/v1/detect", methods=['POST'])
def detect():
    tempFile = tempfile.NamedTemporaryFile()

    try:
        # get model query parameter
        requestedModel = request.args.get("model", DEFAULT_MODEL)

        request_is_invalid = is_invalid_params(request)
        if request_is_invalid:
            return request_is_invalid

        # Download the file
        file = request.files['file']
        tempFile.write(file.read())

        model = whisper.load_model(requestedModel)

        # load audio and pad/trim it to fit 30 seconds
        audio = whisper.load_audio(tempFile.name)
        audio = whisper.pad_or_trim(audio)

        # make log-Mel spectrogram and move to the same device as the model
        mel = whisper.log_mel_spectrogram(audio).to(model.device)

        # detect the spoken language
        _, probs = model.detect_language(mel)
        return {
            "detectedLanguage": max(probs, key=probs.get)
        }
    except Exception as e:
        logging.exception(e)
        return 500
    finally:
        tempFile.close()