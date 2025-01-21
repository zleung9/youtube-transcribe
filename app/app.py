from flask import Flask, render_template
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os
from db_models import Video, Base
# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))



app = Flask(__name__)

# Database setup
engine = create_engine('sqlite:///videos.db', echo=True)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

@app.route('/')
def index():
    session = Session()
    videos = session.query(Video).order_by(Video.processed_date.desc()).all()
    session.close()
    return render_template('index.html', videos=videos)

@app.route('/video/<video_id>')
def video_detail(video_id):
    session = Session()
    video = session.query(Video).filter_by(video_id=video_id).first()
    
    # Read transcript if it exists
    transcript_text = ""
    if video and video.transcript_path:
        try:
            with open(video.transcript_path, 'r', encoding='utf-8') as f:
                transcript_text = f.read()
        except FileNotFoundError:
            transcript_text = "Transcript file not found."
            
    session.close()
    return render_template('video.html', video=video, transcript=transcript_text)

if __name__ == '__main__':
    app.run(debug=True)