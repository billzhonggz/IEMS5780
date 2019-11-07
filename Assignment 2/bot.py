import base64
import logging
import json
import time
import telepot
import requests
import socket
from telepot.loop import MessageLoop
from threading import Thread
from queue import Queue
from io import BytesIO
from PIL import Image

# FIXME: Predict the image from previous image.

# Message queues as global variables.
image_queue = Queue()
output_queue = Queue()


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


def send_to_predict(chat_id):
    """Send images to the server.
    :param chat_id: Telegram chat ID.
    :return str. List of predictions with probabilities. Sorted in descending order.
    """
    # TCP socket initialize.
    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    soc.settimeout(5)
    soc.connect(('localhost', 8888))
    logger.info('Connected to the server.')
    # Encode the image in base64.
    buffered = BytesIO()
    # Get image from queue.
    if not image_queue.empty():
        image = image_queue.get()
    image.save(buffered, format='PNG')
    encoded_image = base64.b64encode(buffered.getvalue())
    data_send = json.dumps(dict({'image': encoded_image.decode('ascii'), 'chat_id': chat_id}))
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
    # Put to queue.
    output_queue.put(predictions)


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
            image_queue.put(i)
            # Feedback to user.
            bot.sendMessage(chat_id, 'Predicting...')
            Thread(target=send_to_predict, args=(chat_id,)).start()
            # Get the result.
            if not output_queue.empty():
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
            # Put to the queue.
            image_queue.put(i)
            # Feedback to user.
            bot.sendMessage(chat_id, 'Predicting...')
            # Pass to predicting server.
            Thread(target=send_to_predict, args=(chat_id,)).start()
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
    logger = get_logger()
    # Provide your bot's token
    bot = telepot.Bot("829334217:AAHdT50M-1SejyMNa8Wug2KlDJThvp5Fxwc")
    logging.info('Bot script starting...')
    MessageLoop(bot, handle).run_as_thread()

    # DEBUG: call prediction function.

    while True:
        time.sleep(10)
