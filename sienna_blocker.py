import datetime
import logging
import json
import os
import random
import sys
import time

from mutagen.mp3 import MP3
import pyttsx3
import vlc
from dejavu import Dejavu
from dejavu.logic.recognizer.microphone_recognizer import MicrophoneRecognizer

DEFAULT_CONFIG_FILE = "dejavu.cnf"


def initialize_dejavu(configpath):
    """
    Load config from a JSON file
    """
    try:
        with open(configpath) as f:
            config = json.load(f)
    except IOError as err:
        print(f"Cannot open configuration: {str(err)}. Exiting")
        sys.exit(1)

    # create a Dejavu instance
    return Dejavu(config)


DAY_TRACKER = {}

GOOD_SONG_PLAYER = None


def respond_to_banned_song(song_name):
    today = datetime.datetime.today().date()

    global DAY_TRACKER
    if today not in DAY_TRACKER:
        DAY_TRACKER = {
            today: {}
        }

    if song_name not in DAY_TRACKER[today]:
        DAY_TRACKER[today][song_name] = 1
    else:
        DAY_TRACKER[today][song_name] += 1

    song_count = DAY_TRACKER[today][song_name]

    if song_count == 1:
        pyttsx3.speak("Estelle, this is the first time playing this song today. You better enjoy it.")
    else:
        message = f"Estelle, you have played this song {song_count} times today. " + \
                  "I'm going to start playing something else now."
        pyttsx3.speak(message)
        good_songs = os.listdir('good_songs')
        random_good_song_name = random.choice(good_songs)
        song_path = os.path.join(os.getcwd(), 'good_songs', random_good_song_name)
        global GOOD_SONG_PLAYER
        GOOD_SONG_PLAYER = vlc.MediaPlayer(song_path)
        GOOD_SONG_PLAYER.play()

        time.sleep(1)


BANNED_SONG_SECONDS_LEFT = -1
INPUT_CONFIDENCE_THRESHOLD = .10

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    banned_songs = []
    for mp3_file in os.listdir('banned_songs'):
        banned_songs.append(mp3_file.replace('.mp3', ''))

    logging.info(f"Watching for banned songs: {banned_songs}")

    djv = initialize_dejavu(DEFAULT_CONFIG_FILE)
    while True:
        if BANNED_SONG_SECONDS_LEFT > 0:
            logging.info(f"Waiting {int(BANNED_SONG_SECONDS_LEFT)}s for banned song to end")
            time.sleep(BANNED_SONG_SECONDS_LEFT)
            BANNED_SONG_SECONDS_LEFT = -1
            logging.info("Done waiting for banned song to end. Moving on...")

        if GOOD_SONG_PLAYER:
            while GOOD_SONG_PLAYER and GOOD_SONG_PLAYER.is_playing():
                logging.info(f"Waiting for good song to end")
                time.sleep(5)
            GOOD_SONG_PLAYER = None
            logging.info("Done waiting for good song to end. Moving on...")

        result = djv.recognize(MicrophoneRecognizer, seconds=10)
        if result is not None and len(result) > 1:
            for song in result[0]:
                song_name = song['song_name'].decode()
                if song_name in banned_songs:
                    logging.info(f"Matched {song_name} with confidence {song['input_confidence']}")
                    if song['input_confidence'] >= INPUT_CONFIDENCE_THRESHOLD:
                        logging.warning(f"Matched {song_name} with confidence {song['input_confidence']}")
                        mp3 = MP3(os.path.join('banned_songs', f"{song_name}.mp3"))
                        BANNED_SONG_SECONDS_LEFT = mp3.info.length - song['offset_seconds']
                        respond_to_banned_song(song_name)
                        break
