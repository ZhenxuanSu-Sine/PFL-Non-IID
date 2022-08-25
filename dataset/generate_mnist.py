import numpy as np
import os
import sys
import random
import torch
import torchvision
import torchvision.transforms as transforms
from utils.dataset_utils import check, separate_data, split_data, save_file
from utils.volminnet.utils import noisify_pairflip

random.seed(1)
np.random.seed(1)
num_clients = 20
num_classes = 10
dir_path = "mnist/"


def noisify(data, noise_rate=0.2, split_per=0.9, random_seed=1, num_classes=10, noise_type='flip'):
    # print(type(data))
    # print(data)
    clean_labels = data[0]['y']
    # print(clean_labels)
    # print(clean_labels.shape)
    noisy_labels, real_noise_rate, transition_matrix = noisify_pairflip(clean_labels,
                                                                              noise=noise_rate,
                                                                              random_state=random_seed,
                                                                              nb_classes=num_classes)
    data[0]['y'] = noisy_labels
    return data, real_noise_rate, transition_matrix

# Allocate data to users
def generate_mnist(dir_path, num_clients, num_classes, niid=False, real=True, partition=None):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        
    # Setup directory for train/test data
    config_path = dir_path + "config.json"
    train_path = dir_path + "train/"
    test_path = dir_path + "test/"

    if check(config_path, train_path, test_path, num_clients, num_classes, niid, real, partition):
        return

    # FIX HTTP Error 403: Forbidden
    from six.moves import urllib
    opener = urllib.request.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    urllib.request.install_opener(opener)

    # Get MNIST data
    transform = transforms.Compose([transforms.ToTensor(), transforms.Normalize([0.5], [0.5])])

    trainset = torchvision.datasets.MNIST(
        root=dir_path+"rawdata", train=True, download=True, transform=transform)
    testset = torchvision.datasets.MNIST(
        root=dir_path+"rawdata", train=False, download=True, transform=transform)
    trainloader = torch.utils.data.DataLoader(
        trainset, batch_size=len(trainset.data), shuffle=False)
    testloader = torch.utils.data.DataLoader(
        testset, batch_size=len(testset.data), shuffle=False)

    for _, train_data in enumerate(trainloader, 0):
        trainset.data, trainset.targets = train_data
    for _, test_data in enumerate(testloader, 0):
        testset.data, testset.targets = test_data

    dataset_image = []
    dataset_label = []

    dataset_image.extend(trainset.data.cpu().detach().numpy())
    dataset_image.extend(testset.data.cpu().detach().numpy())
    dataset_label.extend(trainset.targets.cpu().detach().numpy())
    dataset_label.extend(testset.targets.cpu().detach().numpy())
    dataset_image = np.array(dataset_image)
    dataset_label = np.array(dataset_label)

    # dataset = []
    # for i in range(num_classes):
    #     idx = dataset_label == i
    #     dataset.append(dataset_image[idx])

    X, y, statistic = separate_data((dataset_image, dataset_label), num_clients, num_classes, 
                                    niid, real, partition)
    train_data, test_data = split_data(X, y)
    train_data, real_noisy_rate, transition_matrix = noisify(train_data, noise_rate=0.2, split_per=0.9, random_seed=1, num_classes=10, noise_type='flip')
    save_file(config_path, train_path, test_path, train_data, test_data, real_noisy_rate, transition_matrix, num_clients, num_classes,
        statistic, niid, real, partition)


if __name__ == "__main__":
    niid = True if sys.argv[1] == "noniid" else False
    real = True if sys.argv[2] == "realworld" else False
    partition = sys.argv[3] if sys.argv[3] != "-" else None

    generate_mnist(dir_path, num_clients, num_classes, niid, real, partition)