"""predict.py
This script grab message from message queue 'image',
then do prediction by Inception V3 model,
then send prediction result back to message queue 'prediction'.

This script is a part of a submission of Assignment 3, IEMS5780, S1 2019-2020, CUHK.
Copyright (c)2019 Junru Zhong.
"""

import base64
import json
import logging

import requests
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
from torch.autograd import Variable

from redis import StrictRedis


def get_logger():
    """Initialize logger. Copy from sample code on course website.
    :return logging.Logger.
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s, %(threadName)s, [%(levelname)s] : %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def init_model():
    """Download PyTorch model, load to memory.
    :return: PyTorch model object.
    :return: JSON object. Labels in JSON format.
    """
    # Load model
    model = models.inception_v3(pretrained=True)
    # Download labels.
    labels_content = requests.get(
        'https://s3.amazonaws.com/deep-learning-models/image-models/imagenet_class_index.json').text
    labels = json.loads(labels_content)
    return model, labels


def do_predict(model, labels, image):
    """Do image prediction.
    :param model: PyTorch torvision model.
    :param labels: dictionary. Prediction labels.
    :param image: image to be predicted.
    :return List of dictionaries. With top-5 predicted labels and scores.
    """
    # Normalization parameters. Copy from lecture slides.
    normalize = transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
    # Do image preprocess. Parameters are copied from lecture slides.
    preprocess = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(299),
        transforms.ToTensor(),
        normalize
    ])
    img_tensor = preprocess(image)
    img_tensor.unsqueeze_(0)
    img_variable = Variable(img_tensor)
    # Do prediction.
    model.eval()
    preds = model(img_variable)
    # Convert to text label.
    percentage = torch.nn.functional.softmax(preds, dim=1)[0]
    predictions = []
    for i, score in enumerate(percentage.data.numpy()):
        predictions.append((score, labels[str(i)][1]))
    predictions.sort(reverse=True)
    out = []
    # Top-5 predictions.
    for score, label in predictions[:5]:
        out += [{'label': label, 'score': str(round(score, 2))}]
    return out


if __name__ == '__main__':
    # Enable logging.
    logger = get_logger()
    # Init model.
    model, labels = init_model()
    logger.info('Model initialized.')
    # Initialize message queue.
    # Connect and subscribe
    queue = StrictRedis(host='localhost', port=6379)
    pubsub = queue.pubsub()
    pubsub.subscribe('image')
    logger.info('Subscribed queue \'image\'')
    # Loop to consume from queue 'download'.
    for message in pubsub.listen():
        logger.info("Received {}".format(message))
        msg_data = json.loads(message['data'])
        # Base64 decode.
        image_data = base64.b64decode(msg_data['image'])
        # Save to file
        with open('image.png', 'wb') as outfile:
            outfile.write(image_data)
        # Open image.
        image = Image.open('image.png')
        # Send to predict.
        predictions = do_predict(model, labels, image)
        # Dump predictions to a string with JSON format.
        send_msg = {
            'chatId': msg_data['chatId'],
            'timestamp': msg_data['timestamp'],
            'url': msg_data['url'],
            'predictions': predictions
        }
        queue.publish('prediction', json.dumps(send_msg).encode('utf8'))
