import string

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.transforms as transforms
from PIL import Image

CLASSES = list(string.digits + string.ascii_uppercase)

LETTER_COUNT = 5


class Net(nn.Module):
    def __init__(self):
        super().__init__()
        width = 6
        self.conv1 = nn.Conv2d(1, width, 3, 1)
        self.conv2 = nn.Conv2d(width, 64, 3, 1)
        self.dropout1 = nn.Dropout(0.25)
        self.dropout2 = nn.Dropout(0.5)
        self.fc1 = nn.Linear(33856, 128)
        self.fc2 = nn.Linear(128, len(CLASSES))

    def forward(self, x):
        x = x
        x = self.conv1(x)
        x = F.relu(x)
        x = self.conv2(x)
        x = F.relu(x)
        x = F.max_pool2d(x, 2)
        x = self.dropout1(x)
        x = torch.flatten(x, 1)
        x = self.fc1(x)
        x = F.relu(x)
        x = self.dropout2(x)
        x = self.fc2(x)
        output = F.log_softmax(x, dim=1)
        return output

    def solve_image(self, image: Image.Image) -> str:
        image = image.convert("L")
        transform = transforms.Compose(
            [transforms.ToTensor(), transforms.Normalize((0.5), (0.5))]
        )
        with torch.no_grad():
            self.eval()
            images = [
                transform(x) for x in split_letters(image, letter_count=LETTER_COUNT)
            ]

            outputs = self(torch.stack(images))
            predictions = outputs.argmax(dim=1, keepdim=True)
            return "".join(CLASSES[pred] for pred in predictions)


def split_letters(image, letter_count: int = 5):
    w, h = image.size
    part_width = w / letter_count
    for i in range(letter_count):
        yield image.crop((i * part_width, 0, i * part_width + part_width, h))


def load_net(path: str) -> Net:
    net = Net()
    net.load_state_dict(torch.load(path))
    return net
