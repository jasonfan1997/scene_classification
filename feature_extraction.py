# -*- coding: utf-8 -*-

from __future__ import print_function, division
import torch
from torch.autograd import Variable as V
import torchvision.models as models
from torchvision import transforms as trn
from torch.nn import functional as F
import os
import torch.nn as nn
import torch.optim as optim
import torch.backends.cudnn as cudnn
import numpy as np
import config as cf
import torchvision
import time
import copy
import sys
import argparse
from torchvision import datasets, models, transforms
#from networks import *
from torch.autograd import Variable
from PIL import Image
import pickle

def parse_args():
        
    parser = argparse.ArgumentParser(description='PyTorch Digital Mammography Training')
    parser.add_argument('--lr', default=1e-3, type=float, help='learning_rate')
    parser.add_argument('--net_type', default='resnet50', type=str, help='model')
    #parser.add_argument('--depth', default=50, type=int, help='depth of model')
    parser.add_argument('--finetune', '-f', action='store_true', help='Fine tune pretrained model')
    parser.add_argument('--addlayer','-a',action='store_true', help='Add additional layer in fine-tuning')
    parser.add_argument('--testOnly', '-t', action='store_true', help='Test mode with the saved model')
    args = parser.parse_args()
    return args

	
def main():
    global args
    args = parse_args()
   

    # Phase 1 : Data Upload
    print('\n[Phase 1] : Data Preperation')

    data_dir = cf.test_dir
    # = cf.data_base.split("/")[-1] + os.sep
    print("| Preparing %s dataset..." %(cf.test_dir.split("/")[-1]))

    use_gpu = torch.cuda.is_available()

    # Phase 2 : Model setup
    print('\n[Phase 2] : Model setup')


    def load_model(arch):
        
        #default resnet50
        # load the pre-trained weights
        model_weight = 'whole_%s_places365.pth.tar' % arch
        if not os.access(model_weight, os.W_OK):
            weight_url = 'http://places2.csail.mit.edu/models_places365/whole_%s_places365.pth.tar' % arch
            os.system('wget ' + weight_url)
        model = torch.load(model_weight)
        return model


    def getNetwork(args):
        '''if (args.net_type == '2333'):
            net = VGG(args.finetune, args.depth)
            file_name = 'vgg-%s' %(args.depth)'''
        if args.net_type == 'resnet50':
            #net = resnet(True, 50)
            net = load_model(args.net_type)
            file_name = args.net_type
        else:
            print('Error : Network should be either [VGGNet / ResNet]')
            sys.exit(1)
        return net, file_name

    def softmax(x):
        return np.exp(x) / np.sum(np.exp(x), axis=0)


    print("| Loading checkpoint model for feature extraction...")
    #assert os.path.isdir('checkpoint'), 'Error: No checkpoint directory found!'
    #assert os.path.isdir('checkpoint/'+trainset_dir), 'Error: No model has been trained on the dataset!'
    #_, file_name = getNetwork(args)
    model, file_name = getNetwork(args)
    #checkpoint = torch.load('./checkpoint/'+trainset_dir+file_name+'.t7')
    #model = checkpoint['model']

    print("| Consisting a feature extractor from the model...")
    '''if(args.net_type == 'alexnet' or args.net_type == 'vggnet'):
        feature_map = list(checkpoint['model'].module.classifier.children())
        feature_map.pop()
        new_classifier = nn.Sequential(*feature_map)
        extractor = copy.deepcopy(checkpoint['model'])
        extractor.module.classifier = new_classifier'''
    if (args.net_type == 'resnet50' or 'densenet161'):
        feature_map = list(model.children())
        feature_map.pop()
        # * is used to unpack argument list
        extractor = nn.Sequential(*feature_map)
        
        
        
    if use_gpu:
        model.cuda()
        extractor.cuda()
        cudnn.benchmark = True

    model.eval()
    extractor.eval()
    #both models use 224*224
    sample_input = Variable(torch.randn(1,3,224,224), volatile=True)
    if use_gpu:
        sample_input = sample_input.cuda()

    sample_output = extractor(sample_input)
    featureSize = sample_output.size(1)
    print("| Feature dimension = %d" %featureSize)

    print("\n[Phase 3] : Feature & Score Extraction")

    def is_image(f):
        return f.endswith(".png") or f.endswith(".jpg")

    test_transform = transforms.Compose([
        transforms.Scale((224,224)),
        #transforms.CenterCrop(224),
        transforms.ToTensor(),
        #transforms.Normalize(cf.mean, cf.std)
    ])
    
    output_dir = args.net_type + '_output'
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)
    print('Start saving.')
    count=0
    for subdir, dirs, files in os.walk(data_dir):
        
        for f in files:
            file_path = subdir + os.sep + f
            if (is_image(f)):
                vector_dict = {
                    'file_path': "",
                    'feature': [],
                    'label':"",
                    #'score': 0,
                }

                image = Image.open(file_path).convert('RGB')
                if test_transform is not None:
                    image = test_transform(image)
                inputs = image
                inputs = Variable(inputs, volatile=True)
                if use_gpu:
                    inputs = inputs.cuda()
                inputs = inputs.view(1, inputs.size(0), inputs.size(1), inputs.size(2)) # add batch dim in the front
                features = extractor(inputs).view(featureSize)

                outputs = model(inputs)
                #softmax_res = softmax(outputs.data.cpu().numpy()[0])

                vector_dict['file_path'] = file_path
                #vector_dict['feature'] = features
                vector_dict['feature'] = features.data.cpu().numpy()
                vector_dict['label'] = subdir[-2:]
                #vector_dict['score'] = softmax_res[1]

                vector_file = output_dir + os.sep + os.path.splitext(f)[0] + ".pickle"

                '''
                print(vector_file)
                print(subdir)
                print(vector_dict['feature'].shape)
                print(vector_dict['label'])
                '''
                with open(vector_file, 'wb') as pkl:
                    pickle.dump(vector_dict, pkl, protocol=pickle.HIGHEST_PROTOCOL)
                            
                count +=1
                if count % 100 == 0:
                    print('Count = ' + str(count))
                    

if __name__ == '__main__':
  main()