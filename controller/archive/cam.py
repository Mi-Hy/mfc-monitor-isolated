import cv2
from flask import Flask, Response

app = Flask(__name__)

# Initialiseer de Microdia camera.
# Verander de '0' naar '1' of '2' als je camera op /dev/video1 of /dev/video2 zit.
camera = cv2.VideoCapture(0)

# Optioneel: Stel de resolutie lager in als de stream buffert of hapert
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 960)

def generate_frames():
    while True:
        # Lees het camerabeeld frame voor frame uit
        success, frame = camera.read()
        if not success:
            break
        else:
            # Codeer het frame naar JPEG-formaat
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            # Gebruik het multipart/x-mixed-replace protocol om de frames te streamen
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return '''
    <html>
      <head>
        <title>Microdia USB Camera Stream</title>
      </head>
      <body>
        <h1>Live Microdia Camera Stream</h1>
        <!-- Breedte aangepast naar 640px, hoogte schaalt automatisch mee -->
        <img src="/video_feed" style="width: 640px; max-width: 100%; height: auto;">
      </body>
    </html>
    '''

@app.route('/video_feed')
def video_feed():
    # Retourneer de gegenereerde videostream
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # host='0.0.0.0' zorgt ervoor dat de server bereikbaar is in je hele lokale netwerk
    app.run(host='0.0.0.0', port=5001, debug=False)