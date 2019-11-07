"""model_serving.py
This script runs an TCP server, receive the incoming request for predicting image classes.
This script loads the inception V3 model from PyTorch model zoo. 
This model will be used to do the above prediction.

This script is a part of a submission of Assignment 2, IEMS5780, S1 2019-2020, CUHK.
Copyright (c)2019 Junru Zhong.
"""

import torch
import json
import requests
import logging
import socket
import torchvision.models as models
import torchvision.transforms as transforms

from torch.autograd import Variable
from threading import Thread
from PIL import Image


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


def serve_client(client_socket, address, model, labels):
    """Decodes the message from client, call prediction function. Send back prediction result.
    Adapted from the sample code on course website.
    :param client_socket: socket. Socket object contains client request.
    :param address: str. Client address.
    :param model: PyTorch model object.
    :param labels: str in JSON format. Prediction labels.
    """
    logger.info("Serving client from {}".format(address))
    # TODO: Modify to matching terminating pattern rather than fix length.
    data = client_socket.recv(1024)
    # TODO: Decode image, send to predict, then get the result.
    client_socket.sendall(data)
    client_socket.close()
    logger.info("Finished")


def init_model():
    """Download PyTorch model, load to memory.
    :return: PyTorch model object.
    :return: Labels in JSON format.
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
        out += [{'label': label, 'proba': score}]
    return out


if __name__ == '__main__':
    # Set port number.
    PORT_NUMBER = 8888
    # Enable logging.
    logger = get_logger()
    # Init model.
    model, labels = init_model()
    logger.info('Model initialized.')
    # Start TCP server.
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("localhost", PORT_NUMBER))
    server_socket.listen(10)
    logger.info("Server starts listening for connection...")
    # Accepting client connections.
    while True:
        (client_socket, address) = server_socket.accept()
        logger.info("Accepted connection from {}".format(address))
        client_thread = Thread(target=serve_client,
                               args=(client_socket, address, model, labels),
                               daemon=True)
        client_thread.start()
