from flask import Flask, request, Response
from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration
from viberbot.api.messages.text_message import TextMessage
from viberbot.api.messages.picture_message import PictureMessage
from viberbot.api.messages.keyboard_message import KeyboardMessage
from viberbot.api.viber_requests import ViberConversationStartedRequest
from viberbot.api.viber_requests import ViberFailedRequest
from viberbot.api.viber_requests import ViberMessageRequest

import time
import logging
import sched
import threading
import requests
import json
import param
from rfc import nw
from hana import hdb
from datetime import datetime

# Initialize all objects
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
bw = nw()
db = hdb()
prev_image_nmbr = 0

# Launch Flask
app = Flask(__name__)
viber = Api(BotConfiguration(
    name='BOTNAME',
    avatar='',
    auth_token=param.viber_token
))


@app.route('/', methods=['POST'])
def incoming():
    logger.debug("received request. post data: {0}".format(request.get_data()))

    viber_request = viber.parse_request(request.get_data().decode('utf8'))
    # Welcome message
    if isinstance(viber_request, ViberConversationStartedRequest):
        viber.send_messages(viber_request.user.id, [
            TextMessage(text="Welcome! Please provide some feedback")
        ])

    elif isinstance(viber_request, ViberMessageRequest):

        message_id = str(viber_request.message_token)
        chat_id = str(viber_request.sender.id)
        user_name = viber_request.sender.name
        time_stmp = str(datetime.now())

        if isinstance(viber_request.message, TextMessage):
            message_text = viber_request.message.text
        elif isinstance(viber_request.message, PictureMessage):
            message_text = 'PictureMessage'

            image_url = viber_request.message.media
            headers = {'Ocp-Apim-Subscription-Key': param.azure_subscription_key}

            params = {
                'returnFaceId': 'false',
                'returnFaceLandmarks': 'false',
                'returnFaceAttributes': 'emotion',
            }

            response = requests.post(param.azure_face_api_url, params=params,
                                     headers=headers, json={"url": image_url})

            emotion_result = response.json()

            try:
                emotions = emotion_result[0]['faceAttributes']['emotion']
                print(emotions)
                if (emotions['happiness'] > 0.5) or (emotions['surprise'] > 0.5):
                    message_text = 'Great'
                elif (emotions['neutral'] > 0.5):
                    message_text = 'Not bad'
                elif (emotions['sadness'] > 0.5) or (emotions['anger'] > 0.5 ) or (emotions['anger'] > 0.5 ) \
                        or(emotions['disgust'] > 0.5) or (emotions['fear'] > 0.5 ):
                    message_text = 'So so'

            except IndexError:
                pass

        else:
            message_text = 'Something else'

        # Sending of statistics
        if (chat_id == param.viber_admin_id) and (message_text == 'Send statistics'):
            users = db.get_users()
            statistics = db.get_statistics()

            smiles = {'Great': ' (smiley) ', 'Not bad': ' (straight) ', 'So so': ' (sad) '}
            stat_mess = 'Thank you for voting!\nCurrent statisctics:'
            for statistic in statistics:
                stat_mess = stat_mess + '\n' + str(statistic.column_values[1]) + smiles[
                    statistic.column_values[0]] + str(statistic.column_values[0])

            for user in users:
                viber.send_messages(user.column_values[0], [
                    TextMessage(text=stat_mess)
                ])

        else:
            # Update message in BW
            bw_data = [{'/BIC/ZCHATID': chat_id,
                        '/BIC/ZMESID': message_id,
                        '/BIC/ZCHANNEL': 'Viber',
                        'RECORDMODE': '',
                        '/BIC/ZUSERNM': user_name,
                        '/BIC/ZSTAMP': time_stmp,
                        '/BIC/ZMESS': message_text}]
            try:
                bw.dso_update(bw_data)
            except:
                pass

            # Update message in HANA
            db_data = {'chat_id': chat_id,
                       'message_id': int(message_id),
                       'channel_id': 'Viber',
                       'user_name': user_name,
                       'time_stmp': time_stmp,
                       'message_text': message_text}

            db.table_update(db_data)
            # Voting keyboard JSON
            keyboard = {
                "Type": "keyboard",
                "Buttons": [
                    {
                        "Columns": 2,
                        "Rows": 2,
                        "BgColor": "#00348d",
                        "ActionType": "reply",
                        "ActionBody": "Great",
                        "Text": "<font color=\"#ffffff\" size=\"20\">Great</font>"
                    },
                    {
                        "Columns": 2,
                        "Rows": 2,
                        "BgColor": "#005fb8",
                        "ActionType": "reply",
                        "ActionBody": "Not bad",
                        "Text": "<font color=\"#ffffff\" size=\"20\">Not bad</font>"
                    },
                    {
                        "Columns": 2,
                        "Rows": 2,
                        "BgColor": "#0091da",
                        "ActionType": "reply",
                        "ActionBody": "So so",
                        "Text": "<font color=\"#ffffff\" size=\"20\">So so</font>"
                    }
                ]
            }

            ratings = ["Great", "Not bad", "So so"]

            if (message_text not in ratings):
                viber.send_messages(viber_request.sender.id, [
                    TextMessage(
                        text="Thank you! Please rate:\n(smiley) Great, (straight) Not bad, (sad) So so"),
                    KeyboardMessage(keyboard=keyboard)
                ])
            else:
                statistics = db.get_statistics()

                smiles = {'Great': ' (smiley) ', 'Not bad': ' (straight) ', 'So so': ' (sad) '}
                stat_mess = 'Thank you for voting!\nYou are ' + smiles[message_text] + '\nCurrent result:'

                for statistic in statistics:
                    stat_mess = stat_mess + '\n' + str(statistic.column_values[1]) + smiles[
                        statistic.column_values[0]] + str(statistic.column_values[0])

                viber.send_messages(viber_request.sender.id, [
                    TextMessage(text=stat_mess)
                ])

    elif isinstance(viber_request, ViberFailedRequest):
        logger.warn("client failed receiving message. failure: {0}".format(viber_request))

    return Response(status=200)


def set_webhook(viber):
    viber.set_webhook(param.viber_webhook_url)


if __name__ == "__main__":
    scheduler = sched.scheduler(time.time, time.sleep)
    scheduler.enter(5, 1, set_webhook, (viber,))
    t = threading.Thread(target=scheduler.run)
    t.start()
    # Startin the app
    context = ('webhook_cert.pem', 'webhook_pkey.pem')
    app.run(host='127.0.0.1', port=8443, debug=True, ssl_context=context)
