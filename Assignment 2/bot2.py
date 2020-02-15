import time
import telepot
from telepot.loop import MessageLoop
from telepot.delegate import pave_event_space, per_chat_id, create_open


class MessageCounter(telepot.helper.ChatHandler):
    def __init__(self, *args, **kwargs):
        super(MessageCounter, self).__init__(*args, **kwargs)
        self._count = 0

    def on_chat_message(self, msg):
        self._count += 1
        self.sender.sendMessage(self._count)


class SendToPredict(telepot.helper.ChatHandler):
    def __init__(self, *args, **kwargs):
        super(SendToPredict, self).__init__(*args, **kwargs)
        self._chat_id = 0
        self._help_info = 'To try out the image classification, please send an image or a image URL instead.'

    def on_chat_message(self, msg):
        # Glance message. Direct to different branch.
        content_type, chat_type, self._chat_id = telepot.glance(msg)
        if content_type == 'text':
            self.handle_text_msg(msg)
        elif content_type == 'photo':
            self.handle_photo_msg(msg)
        else:
            self.sender.sendMessage(self._help_info)

    def handle_text_msg(self, msg):
        self.sender.sendMessage('In handle text msg.')
        pass

    def handle_photo_msg(self, msg):
        self.sender.sendMessage('In handle photo msg.')
        pass


TOKEN = 'YOUR API KEY'

bot = telepot.DelegatorBot(TOKEN, [
    pave_event_space()(
        per_chat_id(), create_open, MessageCounter, timeout=10),
])
MessageLoop(bot).run_as_thread()

while 1:
    time.sleep(10)
