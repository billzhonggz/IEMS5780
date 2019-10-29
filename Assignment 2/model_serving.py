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
import torchvision.models as models
import torchvision.transforms as transforms

from torch.autograd import Variable
from PIL import Image


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
        # DEBUG: print the prediction scores.
        print('{:16s}: {:.4f}'.format(label, score))
        out += [{'label': label, 'proba': score}]
    return out


if __name__ == '__main__':
    # Enable logging.
    logging.basicConfig(level=logging.DEBUG)
    # Load model
    model = models.inception_v3(pretrained=True)
    # Download labels.
    labels_content = requests.get('https://s3.amazonaws.com/deep-learning-models/image-models/imagenet_class_index.json').text
    labels = json.loads(labels_content)
    # DEBUG: sample image.
    image = Image.open('image.jpg')
    # Call function
    do_predict(model, labels, image)
