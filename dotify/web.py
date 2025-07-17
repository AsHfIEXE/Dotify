from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from dotify.cli import main as dotify_main
import click
import eventlet

eventlet.monkey_patch()

app = Flask(__name__)
socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        # Save the settings to a config file
        pass
    return render_template('settings.html')

def download_thread(url):
    try:
        # This is a placeholder for the actual download logic
        # In a real application, this would be a long-running task
        # that yields progress updates.
        for i in range(1, 101):
            eventlet.sleep(0.1)
            socketio.emit('progress', {'data': i})
    except Exception as e:
        socketio.emit('progress', {'data': f"An error occurred: {e}"})

@socketio.on('download')
def download(message):
    url = message['url']
    socketio.start_background_task(download_thread, url)

if __name__ == '__main__':
    socketio.run(app, debug=True)
