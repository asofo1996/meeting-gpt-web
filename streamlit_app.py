import streamlit as st
import tempfile
import os
import gspread
from google.cloud import speech
from pydub import AudioSegment
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials

# ✅ 환경 분기
ENV = os.environ.get("DEPLOY_ENV", "local")

if ENV == "render":
    GOOGLE_CREDENTIALS_PATH = "/etc/secrets/central-oath.json"
    SHEET_CREDENTIALS_PATH = "/etc/secrets/credentials.json"
    DRIVE_CLIENT_SECRET_PATH = "/etc/secrets/client_secrets.json"
else:
    SECRET_DIR = os.path.join(os.getcwd(), "secret")
    GOOGLE_CREDENTIALS_PATH = os.path.join(SECRET_DIR, "central-oath-459901-i1-8d436847a32a.json")
    SHEET_CREDENTIALS_PATH = os.path.join(SECRET_DIR, "credentials.json")
    DRIVE_CLIENT_SECRET_PATH = os.path.join(SECRET_DIR, "client_secrets.json")

DRIVE_FOLDER_ID = "1UwU-YRq-3-uRMLT3tRm0D_0fpWda_nm5"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_CREDENTIALS_PATH

# ✅ Google Sheets 인증
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
CREDS = ServiceAccountCredentials.from_json_keyfile_name(SHEET_CREDENTIALS_PATH, SCOPE)
CLIENT = gspread.authorize(CREDS)
SHEET = CLIENT.open("미팅GPT").worksheet("회의기록")

# ✅ Google Drive 업로드 함수
def upload_to_drive(filepath):
    gauth = GoogleAuth()
    gauth.LoadClientConfigFile(DRIVE_CLIENT_SECRET_PATH)
    gauth.LocalWebserverAuth()
    drive = GoogleDrive(gauth)
    file_drive = drive.CreateFile({
        'title': os.path.basename(filepath),
        'parents': [{'id': DRIVE_FOLDER_ID}]
    })
    file_drive.SetContentFile(filepath)
    file_drive.Upload()

# ✅ Google Speech-to-Text 변환 함수
def transcribe(audio_path):
    client = speech.SpeechClient()
    with open(audio_path, "rb") as audio_file:
        content = audio_file.read()
    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="ko-KR",
    )
    response = client.recognize(config=config, audio=audio)
    return " ".join([result.alternatives[0].transcript for result in response.results])

# ✅ Streamlit UI
st.title("🧠 미팅 GPT Web")

audio_file = st.file_uploader("🎙️ 음성 파일 업로드 (WAV/MP3)", type=["wav", "mp3"])

if audio_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        if audio_file.type == "audio/mp3":
            mp3 = AudioSegment.from_file(audio_file, format="mp3")
            mp3.export(tmp.name, format="wav")
        else:
            tmp.write(audio_file.read())
        wav_path = tmp.name

    st.audio(wav_path)

    with st.spinner("🧠 인식 중..."):
        transcript = transcribe(wav_path)

        # ✅ 시트에 20자 단위로 입력
        row = 2
        for i in range(0, len(transcript), 20):
            SHEET.update_cell(row, 2, transcript[i:i+20])
            row += 1

        upload_to_drive(wav_path)

    st.success("✅ 회의 기록 저장 완료!")
    st.text_area("📝 인식 결과", transcript, height=200)
