"""pre_processing.py
This is a part of the Assignment 1, IEMS5780, S1 2019-2020, CUHK
by Junru Zhong
Last modified Oct 6, 2019
"""

import glob
import pandas as pd

from sklearn.model_selection import train_test_split


def combine(dataset_path, is_shuffle=False, save_path=None):
    """Combine the train and test dataset.
    :param: dataset_path: str
    :param: is_shuffle: boolean
    :param: save_path: str, None for don't save
    :return: combined dataset: pandas.Dataframe
    """
    data = []
    # Open files in positive comments.
    for filename in glob.glob(dataset_path + 'train\\pos\\*.txt'):
        with open(filename, 'r', encoding='utf8') as f:
            data += [[f.read().strip(), 1]]
    for filename in glob.glob(dataset_path + 'test\\pos\\*.txt'):
        with open(filename, 'r', encoding='utf8') as f:
            data += [[f.read().strip(), 1]]
    # Open files in negative comments.
    for filename in glob.glob(dataset_path + 'train\\neg\\*.txt'):
        with open(filename, 'r', encoding='utf8') as f:
            data += [[f.read().strip(), 0]]
    for filename in glob.glob(dataset_path + 'test\\neg\\*.txt'):
        with open(filename, 'r', encoding='utf8') as f:
            data += [[f.read().strip(), 0]]

    # Load datalist into DataFrame
    df = pd.DataFrame(data, columns=['comment', 'attitude'])
    # Shuffle
    if is_shuffle:
        df = df.sample(frac=1)
    # Split the dataset
    df_train, df_test = train_test_split(df, test_size=0.3)
    # Save DataFrame to csv file.
    if save_path is not None:
        with open(save_path + 'train.csv', 'w', encoding='utf8') as f:
            df_train.to_csv(f)
        with open(save_path + 'test.csv', 'w', encoding='utf8') as f:
            df_test.to_csv(f)
    # Return the dataframe.
    return df_train, df_test


if __name__ == '__main__':
    combine('E:\\Datasets\\aclImdb\\', True, 'E:\\Datasets\\aclImdb\\')
