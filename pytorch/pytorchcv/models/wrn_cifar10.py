"""
    WRN for CIFAR-10, implemented in PyTorch.
    Original paper: 'Wide Residual Networks,' https://arxiv.org/abs/1605.07146.
"""

__all__ = ['CIFAR10WRN', 'wrn16_10_cifar10', 'wrn28_10_cifar10', 'wrn40_8_cifar10']

import os
import torch.nn as nn
import torch.nn.init as init
from .common import conv3x3_block
from .preresnet import PreResUnit, PreResActivation


class CIFAR10WRN(nn.Module):
    """
    CIFAR-10 WRN model from 'Wide Residual Networks,' https://arxiv.org/abs/1605.07146.

    Parameters:
    ----------
    channels : list of list of int
        Number of output channels for each unit.
    init_block_channels : int
        Number of output channels for the initial unit.
    in_channels : int, default 3
        Number of input channels.
    in_size : tuple of two ints, default (32, 32)
        Spatial size of the expected input image.
    num_classes : int, default 10
        Number of classification classes.
    """
    def __init__(self,
                 channels,
                 init_block_channels,
                 in_channels=3,
                 in_size=(32, 32),
                 num_classes=10):
        super(CIFAR10WRN, self).__init__()
        self.in_size = in_size
        self.num_classes = num_classes

        self.features = nn.Sequential()
        self.features.add_module("init_block_pre", nn.BatchNorm2d(
            num_features=in_channels,
            affine=False))
        self.features.add_module("init_block", conv3x3_block(
            in_channels=in_channels,
            out_channels=init_block_channels,
            activation=None,
            activate=False))
        in_channels = init_block_channels
        for i, channels_per_stage in enumerate(channels):
            stage = nn.Sequential()
            for j, out_channels in enumerate(channels_per_stage):
                stride = 2 if (j == 0) and (i != 0) else 1
                stage.add_module("unit{}".format(j + 1), PreResUnit(
                    in_channels=in_channels,
                    out_channels=out_channels,
                    stride=stride,
                    bottleneck=False,
                    conv1_stride=False))
                in_channels = out_channels
            self.features.add_module("stage{}".format(i + 1), stage)
        self.features.add_module("post_activ", PreResActivation(in_channels=in_channels))
        self.features.add_module("final_pool", nn.AvgPool2d(
            kernel_size=8,
            stride=1))

        self.output = nn.Linear(
            in_features=in_channels,
            out_features=num_classes)

        self._init_params()

    def _init_params(self):
        for name, module in self.named_modules():
            if isinstance(module, nn.Conv2d):
                init.kaiming_uniform_(module.weight)
                if module.bias is not None:
                    init.constant_(module.bias, 0)

    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        x = self.output(x)
        return x


def get_wrn(blocks,
            width_factor,
            model_name=None,
            pretrained=False,
            root=os.path.join('~', '.torch', 'models'),
            **kwargs):
    """
    Create WRN model for CIFAR-10 with specific parameters.

    Parameters:
    ----------
    blocks : int
        Number of blocks.
    width_factor : int
        Wide scale factor for width of layers.
    model_name : str or None, default None
        Model name for loading pretrained model.
    pretrained : bool, default False
        Whether to load the pretrained weights for model.
    root : str, default '~/.torch/models'
        Location for keeping the model parameters.
    """

    assert ((blocks - 4) % 6 == 0)
    layers = [(blocks - 4) // 6] * 3
    channels_per_layers = [16, 32, 64]
    init_block_channels = 16

    channels = [[ci * width_factor] * li for (ci, li) in zip(channels_per_layers, layers)]

    net = CIFAR10WRN(
        channels=channels,
        init_block_channels=init_block_channels,
        **kwargs)

    if pretrained:
        if (model_name is None) or (not model_name):
            raise ValueError("Parameter `model_name` should be properly initialized for loading pretrained model.")
        from .model_store import download_model
        download_model(
            net=net,
            model_name=model_name,
            local_model_store_dir_path=root)

    return net


def wrn16_10_cifar10(**kwargs):
    """
    WRN-16-10 model for CIFAR-10 from 'Wide Residual Networks,' https://arxiv.org/abs/1605.07146.

    Parameters:
    ----------
    pretrained : bool, default False
        Whether to load the pretrained weights for model.
    root : str, default '~/.torch/models'
        Location for keeping the model parameters.
    """
    return get_wrn(blocks=16, width_factor=10, model_name="wrn16_10_cifar10", **kwargs)


def wrn28_10_cifar10(**kwargs):
    """
    WRN-28-10 model for CIFAR-10 from 'Wide Residual Networks,' https://arxiv.org/abs/1605.07146.

    Parameters:
    ----------
    pretrained : bool, default False
        Whether to load the pretrained weights for model.
    root : str, default '~/.torch/models'
        Location for keeping the model parameters.
    """
    return get_wrn(blocks=28, width_factor=10, model_name="wrn28_10_cifar10", **kwargs)


def wrn40_8_cifar10(**kwargs):
    """
    WRN-40-8 model for CIFAR-10 from 'Wide Residual Networks,' https://arxiv.org/abs/1605.07146.

    Parameters:
    ----------
    pretrained : bool, default False
        Whether to load the pretrained weights for model.
    root : str, default '~/.torch/models'
        Location for keeping the model parameters.
    """
    return get_wrn(blocks=40, width_factor=8, model_name="wrn40_8_cifar10", **kwargs)


def _calc_width(net):
    import numpy as np
    net_params = filter(lambda p: p.requires_grad, net.parameters())
    weight_count = 0
    for param in net_params:
        weight_count += np.prod(param.size())
    return weight_count


def _test():
    import torch
    from torch.autograd import Variable

    pretrained = False

    models = [
        wrn16_10_cifar10,
        wrn28_10_cifar10,
        wrn40_8_cifar10,
    ]

    for model in models:

        net = model(pretrained=pretrained)

        # net.train()
        net.eval()
        weight_count = _calc_width(net)
        print("m={}, {}".format(model.__name__, weight_count))
        assert (model != wrn16_10_cifar10 or weight_count == 17116666)
        assert (model != wrn28_10_cifar10 or weight_count == 36479226)
        assert (model != wrn40_8_cifar10 or weight_count == 35748346)

        x = Variable(torch.randn(1, 3, 32, 32))
        y = net(x)
        assert (tuple(y.size()) == (1, 10))


if __name__ == "__main__":
    _test()
