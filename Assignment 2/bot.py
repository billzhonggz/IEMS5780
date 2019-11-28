"""bot.py
This script creates three threads to do the following,
Thread 1 (created by Telepot): Receiving messages from Telegram
Thread 2: Handle incoming message from queue, send to predict.
Thread 3 (created by Telepot): Send prediction results back to user.

This script is a part of a submission of Assignment 2, IEMS5780, S1 2019-2020, CUHK.
Copyright (c)2019 Junru Zhong.
"""
import base64
import json
import logging
import socket
import time
from io import BytesIO
from queue import Queue
from threading import Thread

import requests
import telepot
from PIL import Image
from telepot.loop import MessageLoop


def get_logger():
    """Initialize logger. Copy from sample code on course website.
    :return logging.Logger.
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s, %(threadName)s, [%(levelname)s] : %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def send_to_predict():
    """Send images to the server.
    :param chat_id: Telegram chat ID.
    :return str. List of predictions with probabilities. Sorted in descending order.
    """
    logger.info('Predicting thread started.')
    # Waiting for incoming images.
    while not image_queue.empty():
        # Predict all images in the queue.
        # Get image from queue.
        incoming_message = image_queue.get()
        # TCP socket initialize.
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        soc.settimeout(5)
        soc.connect(('localhost', 8888))
        logger.info('Connected to the server.')
        # Encode the image in base64.
        buffered = BytesIO()
        image = incoming_message['image']
        image.save(buffered, format='PNG')
        encoded_image = base64.b64encode(buffered.getvalue())
        data_send = json.dumps(dict({'image': encoded_image.decode('ascii'), 'chat_id': incoming_message['chat_id']}))
        # TCP client: encoded image send to the server. Waiting for receiving predictions.
        terminate = '##END##'
        data_send += terminate
        soc.sendall(str.encode(data_send, 'utf8'))
        chunks = []
        while True:
            current_data = soc.recv(8192).decode('utf8', 'strict')
            if terminate in current_data:
                chunks.append(current_data[:current_data.find(terminate)])
                break
            chunks.append(current_data)
            if len(chunks) > 1:
                last_pair = chunks[-2] + chunks[-1]
                if terminate in last_pair:
                    chunks[-2] = last_pair[:last_pair.find(terminate)]
                    chunks.pop()
                    break
        received_data = ''.join(chunks)
        # JSON decode.
        decoded_data = json.loads(received_data)
        # Format
        predictions = ''
        idx = 1
        for item in decoded_data['predictions']:
            predictions += '{}. {} ({})\n'.format(idx, item['label'], item['proba'])
            idx += 1
        send_back = {
            'predictions': predictions,
            'chat_id': incoming_message['chat_id']
        }
        # Put to queue.
        output_queue.put(send_back)


def send_predictions_back():
    """Keep polling the output queue, send back the predictions to users."""
    # Waiting for incoming predictions.
    logger.info('Send back thread started.')
    while not output_queue.empty():
        # Send all predictions back.
        send_back = output_queue.get()
        # Send message.
        bot.sendMessage(send_back['chat_id'], send_back['predictions'])


def handle(msg):
    """
    A function that will be invoked when a message is
    recevied by the bot
    """
    content_type, chat_type, chat_id = telepot.glance(msg)
    logging.info('Handling incoming message {}.'.format(chat_id))

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
            message_to_predict = {'image': i, 'chat_id': chat_id}
            image_queue.put(message_to_predict)
            # Feedback to user.
            # bot.sendMessage(chat_id, 'Predicting...')
            # Thread(target=send_to_predict, args=(chat_id,), daemon=True).start()
            # Get the result.
            # predictions = output_queue.get()
            # Return predictions to the client.
            # bot.sendMessage(chat_id, predictions)
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
            # Put to the queue.
            message_to_predict = {'image': i, 'chat_id': chat_id}
            image_queue.put(message_to_predict)
            # Feedback to user.
            # bot.sendMessage(chat_id, 'Predicting...')
            # Pass to predicting server.
            # Thread(target=send_to_predict, args=(chat_id,), daemon=True).start()
            # Get the result.
            # predictions = output_queue.get()
            # Return predictions to the client.
            # bot.sendMessage(chat_id, predictions)
        except Exception as e:
            error_info = 'An exception was caught when handling incoming image: {}'.format(str(e))
            logging.WARNING(error_info)
            bot.sendMessage(chat_id, error_info)


if __name__ == "__main__":
    # Message queues as global variables.
    image_queue = Queue()
    output_queue = Queue()
    logger = get_logger()
    # Provide your bot's token
    bot = telepot.Bot("829334217:AAHdT50M-1SejyMNa8Wug2KlDJThvp5Fxwc")
    logger.info('Bot script starting...')
    MessageLoop(bot, handle).run_as_thread()
    # Start threads.
    send_to_predict_thread = Thread(target=send_to_predict, daemon=True)
    send_back_thread = Thread(target=send_predictions_back, daemon=True)
    send_to_predict_thread.start()
    send_back_thread.start()
    send_to_predict_thread.join()
    send_back_thread.join()

    # DEBUG: call prediction function.

    while True:
        time.sleep(10)
