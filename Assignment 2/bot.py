import base64
import logging
import json
import re
import time
import telepot
import requests
from telepot.loop import MessageLoop
from threading import Thread
from queue import Queue
from io import BytesIO
from PIL import Image


def send_to_predict(image, chat_id, output_queue):
    """Send images to the server.
    :param image: PIL image. The incoming images.
    :param chat_id: Telegram chat ID.
    :param output_queue: Output prediction through a queue.
    :return str. List of predictions with probabilities. Sorted in descending order.
    """
    # Encode the image in base64.
    buffered = BytesIO()
    image.save(buffered, format='PNG')
    encoded_image = base64.b64encode(buffered.getvalue())
    data_send = json.dumps(dict({'image': encoded_image.decode('ascii'), 'chat_id': chat_id}))
    output_queue.put(data_send)
    # TODO: TCP client: encoded image send to the server. Waiting for receiving predictions.
    # predictions = ''
    # return predictions
    return data_send


def handle(msg):
    """
    A function that will be invoked when a message is
    recevied by the bot
    """
    content_type, chat_type, chat_id = telepot.glance(msg)
    logging.info('Handling incoming message {}.'.format(chat_id))
    # Initialize the queue.
    output_queue = Queue()

    if content_type == "text":
        content = msg["text"]
        # Try to download URL.
        try:
            image_response = requests.get(content)
            if image_response.status_code != 200:
                raise Exception('Response code is not 200 OK.')
            if 'image' not in image_response.headers['content-type']:
                raise Exception('The URL does not contains an image.')
            i = Image.open(BytesIO(image_response.content))
            # Pass to predicting server.
            # Feedback to user.
            bot.sendMessage(chat_id, 'Predicting...')
            Thread(target=send_to_predict, args=(i, chat_id, output_queue)).start()
            # TODO: add a blocking.
            # Get the result.
            with not output_queue.empty():
                predictions = output_queue.get()
            # Return predictions to the client.
            bot.sendMessage(chat_id, predictions)
        except Exception as e:
            help_info = 'To try out the image classification, please send an image or a image URL instead.'
            reply = "You said: {}\n{}\n{}".format(content, help_info, str(e))
            bot.sendMessage(chat_id, reply)
            return

    # Handle photos.
    if content_type == 'photo':
        try:
            # Download image.
            bot.download_file(msg['photo'][-1]['file_id'], 'file.png')
            # Open the image.
            i = Image.open('file.png')
            # Feedback to user.
            bot.sendMessage(chat_id, 'Predicting...')
            # Pass to predicting server.
            Thread(target=send_to_predict, args=(i, chat_id, output_queue)).start()
            # TODO: add a blocking.
            # Get the result.
            if not output_queue.empty():
                predictions = output_queue.get()
            # Return predictions to the client.
            bot.sendMessage(chat_id, predictions)
        except Exception as e:
            error_info = 'An exception was caught when handling incoming image: {}'.format(str(e))
            logging.WARNING(error_info)
            bot.sendMessage(chat_id, error_info)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    # Provide your bot's token
    bot = telepot.Bot("829334217:AAHdT50M-1SejyMNa8Wug2KlDJThvp5Fxwc")
    logging.info('Bot script starting...')
    # TODO: inspect how `handle()` function run beneath telepot API.
    MessageLoop(bot, handle).run_as_thread()

    while True:
        time.sleep(10)
