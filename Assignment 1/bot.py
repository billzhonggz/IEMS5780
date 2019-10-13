import time
import telepot
from telepot.loop import MessageLoop

from joblib import load


def handle(msg):
    """
    A function that will be invoked when a message is
    recevied by the bot
    """
    # Load model
    # TODO: load model before entering this function.
    model = load('model.joblib')
    content_type, chat_type, chat_id = telepot.glance(msg)

    if content_type == "text":
        content = msg["text"]
        predict = 'positive' if model.predict([content])[0] else 'negative'
        reply = "You said: {}\nThis comment is {}.".format(content, predict)
        bot.sendMessage(chat_id, reply)

if __name__ == "__main__":
    # Provide your bot's token
    bot = telepot.Bot("829334217:AAHdT50M-1SejyMNa8Wug2KlDJThvp5Fxwc")
    MessageLoop(bot, handle).run_as_thread()

    while True:
        time.sleep(10)