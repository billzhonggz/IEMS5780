import base64
import logging
import time
import telepot
from telepot.loop import MessageLoop
from io import BytesIO
from PIL import Image


def send_to_predict(image):
    """Send images to the server.
    :param image: PIL.Image object. Incoming image.
    :return str. List of predictions with probabilities. Sorted in descending order.
    """
    # Encode the image in base64.
    buffered = BytesIO()
    image.save(buffered, format='PNG')
    encoded_image = base64.b64encode(buffered.getvalue())
    # TODO: TCP client: encoded image send to the server. Waiting for receiving predictions.
    predictions = ''
    return predictions


def handle(msg):
    """
    A function that will be invoked when a message is
    recevied by the bot
    """
    content_type, chat_type, chat_id = telepot.glance(msg)

    if content_type == "text":
        content = msg["text"]
        help_info = 'To try out the image classification, please send an image instead.'
        reply = "You said: {}\n{}".format(content, help_info)
        bot.sendMessage(chat_id, reply)

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
            # TODO: change to a queue.
            predictions = send_to_predict(i)
            # Return predictions to the client.
            bot.sendMessage(chat_id, predictions)
        except Exception as e:
            error_info = 'An exception was caught when handling incoming image: {}'.format(str(e))
            logging.WARNING(error_info)
            bot.sendMessage(chat_id, error_info)


if __name__ == "__main__":

    # Provide your bot's token
    bot = telepot.Bot("829334217:AAHdT50M-1SejyMNa8Wug2KlDJThvp5Fxwc")
    MessageLoop(bot, handle).run_as_thread()

    while True:
        time.sleep(10)
