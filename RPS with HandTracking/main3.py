import cv2
import time
import random
import numpy as np
from flask import Flask, render_template_string, request, Response
from cvzone.HandTrackingModule import HandDetector
import cvzone
import io
from PIL import Image

app = Flask(__name__)

# Game Variables
detector = HandDetector(maxHands=1)
timer = 0
startGame = False
stateResult = False
initialTime = 0
playerMove = 0
Scores = [0, 0]  # [AI, Player]
imgAI = None

# Load background
imgBG = cv2.imread('Resources/BG.png')


@app.route('/')
def index():
    return render_template_string('''
        <html>
        <head>
            <title>Webcam Streaming</title>
        </head>
        <body>
            <h1>Webcam Streaming</h1>
            <video id="video" width="640" height="480" autoplay></video>
            <canvas id="canvas" style="display:none;"></canvas>
            <img id="output" src="" width="1280" height="720" />
            <script>
                const video = document.getElementById('video');
                const canvas = document.getElementById('canvas');
                const output = document.getElementById('output');
                const context = canvas.getContext('2d');

                navigator.mediaDevices.getUserMedia({ video: true })
                    .then(stream => {
                        video.srcObject = stream;
                    });

                setInterval(() => {
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    context.drawImage(video, 0, 0, canvas.width, canvas.height);
                    canvas.toBlob(blob => {
                        const formData = new FormData();
                        formData.append('frame', blob);

                        fetch('/upload', {
                            method: 'POST',
                            body: formData
                        })
                        .then(response => response.blob())
                        .then(imageBlob => {
                            const url = URL.createObjectURL(imageBlob);
                            output.src = url;
                        });
                    }, 'image/jpeg');
                }, 100);

                // Press 's' to start the game
                window.addEventListener('keydown', (event) => {
                    if (event.key === 's' || event.key === 'S') {
                        fetch('/start').then(res => console.log('Game Started'));
                    }
                });
            </script>
        </body>
        </html>
    ''')


@app.route('/upload', methods=['POST'])
def upload():
    global timer, startGame, stateResult, initialTime, playerMove, Scores, imgAI
    file = request.files['frame']
    in_memory_file = io.BytesIO()
    file.save(in_memory_file)
    data = np.frombuffer(in_memory_file.getvalue(), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)

    imgBG_copy = imgBG.copy()
    imgScaled = cv2.resize(img, (0, 0), None, 0.875, 0.875)
    imgScaled = imgScaled[:, 80:480]

    hands, img = detector.findHands(imgScaled)

    if startGame:
        if stateResult is False:
            timer = time.time() - initialTime
            cv2.putText(imgBG_copy, str(int(timer)), (605, 435), cv2.FONT_HERSHEY_PLAIN, 6, (255, 0, 255), 4)

            if timer > 3:
                stateResult = True
                timer = 0

                if hands:
                    hand = hands[0]
                    fingers = detector.fingersUp(hand)
                    if fingers == [0, 0, 0, 0, 0]:
                        playerMove = 1
                    elif fingers == [1, 1, 1, 1, 1]:
                        playerMove = 2
                    elif fingers == [0, 1, 1, 0, 0]:
                        playerMove = 3

                    randomNumber = random.randint(1, 3)
                    imgAI = cv2.imread(f'Resources/{randomNumber}.png', cv2.IMREAD_UNCHANGED)
                    imgBG_copy = cvzone.overlayPNG(imgBG_copy, imgAI, (149, 310))

                    # Win check
                    if (playerMove == 1 and randomNumber == 3) or \
                       (playerMove == 3 and randomNumber == 2) or \
                       (playerMove == 2 and randomNumber == 1):
                        Scores[1] += 1
                    elif (playerMove == 3 and randomNumber == 1) or \
                         (playerMove == 2 and randomNumber == 3) or \
                         (playerMove == 1 and randomNumber == 3):
                        Scores[0] += 1

    imgBG_copy[234:654, 795:1195] = imgScaled
    if stateResult and imgAI is not None:
        imgBG_copy = cvzone.overlayPNG(imgBG_copy, imgAI, (149, 310))

    cv2.putText(imgBG_copy, str(Scores[0]), (410, 215), cv2.FONT_HERSHEY_PLAIN, 4, (255, 255, 255), 6)
    cv2.putText(imgBG_copy, str(Scores[1]), (1112, 215), cv2.FONT_HERSHEY_PLAIN, 4, (255, 255, 255), 6)

    _, jpeg = cv2.imencode('.jpg', imgBG_copy)
    return Response(jpeg.tobytes(), mimetype='image/jpeg')


@app.route('/start')
def start():
    global startGame, initialTime, stateResult
    startGame = True
    initialTime = time.time()
    stateResult = False
    return "Game Started"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860)
