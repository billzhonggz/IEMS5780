"""model_serving.py
Thread 1: TCP server, receive the incoming request for predicting image classes.
Thread 2: loads the inception V3 model from PyTorch model zoo, and uses it to do the above prediction. Then return the result.

This script is a part of a submission of Assignment 2, IEMS5780, S1 2019-2020, CUHK.
Copyright (c)2019 Junru Zhong.
"""

import base64
import json
import logging
import socket
from queue import Queue
from threading import Thread

import requests
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
from torch.autograd import Variable


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


def tcp_server(port, input_queue):
    logger.info("Server thread starts. Listening for connection...")
    # Start TCP server.
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("localhost", port))
    server_socket.listen(10)
    # Accepting client connections.
    while True:
        (client_socket, address) = server_socket.accept()
        logger.info("Accepted connection from {}".format(address))
        input_queue.put((client_socket, address))
        logger.debug('Current size of input_queue is {}.'.format(input_queue.qsize()))


def serve_client(input_queue, model, labels):
    """Decodes the message from client, call prediction function. Send back prediction result.
    Adapted from the sample code on course website.
    :param model: PyTorch model object.
    :param labels: JSON object. Prediction labels.
    """
    logger.info('Prediction thread starts...')
    while True:
        if not input_queue.empty():
            logger.debug('Current size of input_queue is {}.'.format(input_queue.qsize()))
            (client_socket, address) = input_queue.get()
            logger.info("Serving client from {}".format(address))
            # Terminating string.
            terminate = '##END##'
            chunks = []
            while True:
                current_data = client_socket.recv(8192).decode('utf8', 'strict')
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
            # JSON decode
            received_data = json.loads(received_data)
            # Base64 decode
            image_data = base64.b64decode(received_data['image'])
            with open('image.png', 'wb') as outfile:
                outfile.write(image_data)
            # Open image.
            image = Image.open('image.png')
            # Send to predict.
            predictions = do_predict(model, labels, image)
            # Dump predictions to a string with JSON format.
            send_data = {'predictions': predictions, 'chat_id': received_data['chat_id']}
            send_data = json.dumps(send_data)
            # Add terminating string.
            send_data += terminate
            # Send back to client.
            client_socket.sendall(send_data.encode('utf8'))
            client_socket.close()
            logger.info("Finished serving {}.".format(address))


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
        out += [{'label': label, 'proba': str(round(score, 2))}]
    return out


if __name__ == '__main__':
    # Set port number.
    PORT_NUMBER = 8888
    # Enable logging.
    logger = get_logger()
    # Init model.
    model, labels = init_model()
    logger.info('Model initialized.')
    # Init queue
    input_queue = Queue()
    # Start threads.
    tcp_server_thread = Thread(target=tcp_server, args=(PORT_NUMBER, input_queue), daemon=True)
    prediction_thread = Thread(target=serve_client, args=(input_queue, model, labels), daemon=True)
    tcp_server_thread.start()
    prediction_thread.start()
    tcp_server_thread.join()
    prediction_thread.join()
