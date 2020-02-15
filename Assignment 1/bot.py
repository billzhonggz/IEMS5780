"""bot.py
Handling Telegram Bot.
A part of Assignment 1, IEMS5780, CUHK, S1 2019-2020

Written by: Junru Zhong
"""

import time
import telepot
from telepot.loop import MessageLoop

from joblib import load

# Load model as a global variable.
# Change to your path to the model file.
model = load('model.joblib')

def handle(msg):
    """
    A function that will be invoked when a message is
    received by the bot
    """
    # Get themessage.
    content_type, chat_type, chat_id = telepot.glance(msg)

    if content_type == "text":
        # Gather message text.
        content = msg["text"]
        # Do prediction.
        predict = model.predict_proba([content])
        predict = predict.flatten().tolist()

        # DEBUG, predict[0] -> neg; predict[1] -> pos
        print(predict)

        # Check the probabilities of both classes,
        # output the winner class and its probability.
        if predict[0] < predict[1]:
            predict_text = 'positive'
            predict_precentage = round(predict[1], 2)
        elif predict[0] > predict[1]:
            predict_text = 'negative'
            predict_precentage = round(predict[0], 2)
        else:
            predict_text = 'not sure'
            predict_precentage = round(predict[0], 2)
        # Construct reply message.
        reply = "This is a {} input! ({}).".format(predict_text, predict_precentage)
        bot.sendMessage(chat_id, reply)

if __name__ == "__main__":
    # Provide your bot's token
    bot = telepot.Bot("YOUR API KEY")
    MessageLoop(bot, handle).run_as_thread()

    while True:
        time.sleep(10)