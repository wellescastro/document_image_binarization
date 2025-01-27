from torch.utils.data.dataset import Dataset
from torchvision import transforms
from glob import glob
import cv2
import numpy as np
from random import shuffle
from skimage.util.shape import view_as_blocks
import random
from PIL import Image
import torch
# from util.sliding_window import sliding_window_view
from .sliding_window import sliding_window_view
from sklearn.preprocessing import minmax_scale

class DIBCODataset(Dataset):

    DIBCO = {
        2009: ['handwritten', 'printed'],
        2010: ['handwritten'],
        2011: ['handwritten', 'printed'],
        2012: ['handwritten'],
        2013: ['handwritten', 'printed'],
        2014: ['handwritten'],
        2016: ['handwritten']
    }

    def __init__(self, basepath="data/Dibco", years=[2009,2010,2011,2012,2013,2014], transform=None, target_transform=None, window_size=(256,256), stride=(128,128), include_augmentation=True):
        self.data_files = []
        for year in years:
            for subset in self.DIBCO[year]:
                dibco_imgs_path = "{}/{}/{}_GR/".format(basepath, year, subset)
                self.data_files.extend(glob(dibco_imgs_path + "*.png"))

                if include_augmentation:
                    dibco_imgs_path = dibco_imgs_path.replace("_GR", "_GR_aug")
                    self.data_files.extend(glob(dibco_imgs_path + "*.png"))

        # self.data_files = sorted(data_files)
        shuffle(self.data_files)

        X_train = []
        Y_train = []
        list_of_patches = []

        for filename_gr in self.data_files:
            filename_gt = filename_gr.replace("GR", "GT")
                           
            img_gr = cv2.imread(filename_gr, cv2.IMREAD_GRAYSCALE)
            img_gt = cv2.imread(filename_gt, cv2.IMREAD_GRAYSCALE)

            img_gr_h, img_gr_w = img_gr.shape

            # resize image to the nearest shape divisible per the window size
            # new_gr_h, new_gr_w = int( window_size[0] * round( float(img_gr_h) / window_size[0] )), int( window_size[1] * round( float(img_gr_w) / window_size[1] ))
            # img_gr = cv2.resize(img_gr, (new_gr_w, new_gr_h), interpolation = cv2.INTER_CUBIC)
            # img_gt = cv2.resize(img_gt, (new_gr_w, new_gr_h), interpolation = cv2.INTER_CUBIC)

            # TODO: implement the skip window approach
            # TODO: implement a crop approach based on the minimum divisible number by the window size
            
            # apply padding instead of resizing to avoid losing significant information
            horizontal_padding = int(window_size[1] * np.ceil( float(img_gr_w) / window_size[1] ) - img_gr_w)
            vertical_padding = int(window_size[0] * np.ceil( float(img_gr_h) / window_size[0] ) - img_gr_h)

            img_gr = np.pad(img_gr, ((vertical_padding // 2, vertical_padding // 2 + vertical_padding % 2),(horizontal_padding // 2, horizontal_padding // 2 + horizontal_padding % 2)), mode='constant', constant_values=255)
            img_gt = np.pad(img_gt, ((vertical_padding // 2, vertical_padding // 2 + vertical_padding % 2),(horizontal_padding // 2, horizontal_padding // 2 + horizontal_padding % 2)), mode='constant', constant_values=255)
            
            # sliding window approach, there are three alternatives but only the last one allows specifying the stride
            # img_gr_patches = view_as_blocks(img_gr, window_size).reshape(-1, window_size[0], window_size[1]) 
            # img_gt_patches = view_as_blocks(img_gt, window_size).reshape(-1, window_size[0], window_size[1])
            # img_gr_patches = self.blockshaped(img_gr, window_size[0], window_size[1])
            # img_gt_patches = self.blockshaped(img_gt, window_size[0], window_size[1])

            img_gr_patches = sliding_window_view(img_gr, window_size, step=stride)
            img_gt_patches = sliding_window_view(img_gt, window_size, step=stride)
            img_gr_patches = img_gr_patches.reshape(-1, window_size[0], window_size[1])
            img_gt_patches = img_gt_patches.reshape(-1, window_size[0], window_size[1])
            
            # sanity check of the sliding window approach, disable reshaping before the test
            # img_gr_reconstructed = np.zeros(img_gr.shape, dtype=np.uint8)
            # for ind1, row_of_patches in enumerate(img_gr_patches):
            #     for ind2, patch in enumerate(row_of_patches):
            #         i_0 = ind1 * stride[0]
            #         i_f = i_0 + window_size[0]
            #         j_0 = ind2 * stride[1]
            #         j_f = j_0 + window_size[1]
            #         img_gr_reconstructed[i_0:i_f, j_0:j_f] = patch
            
            # img_gt_reconstructed = np.zeros(img_gt.shape, dtype=np.uint8)
            # for ind1, row_of_patches in enumerate(img_gt_patches):
            #     for ind2, patch in enumerate(row_of_patches):
            #         i_0 = ind1 * stride[0]
            #         i_f = i_0 + window_size[0]
            #         j_0 = ind2 * stride[1]
            #         j_f = j_0 + window_size[1]
            #         img_gt_reconstructed[i_0:i_f, j_0:j_f] = patch
   
            X_train.extend(img_gr_patches)
            Y_train.extend(img_gt_patches)
            list_of_patches.append(len(img_gr_patches))
        
        X_train = np.asarray(X_train)
        Y_train = np.asarray(Y_train)

        X_train = 255 - X_train
        Y_train = 255 - Y_train

        self.X_train = X_train
        self.Y_train = Y_train
        self.transform = transform
        self.target_transform = target_transform
        self.list_of_patches = list_of_patches
    

    def __getitem__(self, index):
        # img_gr = Image.fromarray(self.X_train[index]) # disabled since i'm using ToPILImage transform
        # img_gt = Image.fromarray(self.Y_train[index]) # disabled since i'm using ToPILImage transform
        img_gr = self.X_train[index]
        img_gt = self.Y_train[index]
        
        # match PIL shape requirements
        # img_gr = np.expand_dims(img_gr, 2)
        # img_gt = np.expand_dims(img_gt, 2)
        
        seed = np.random.randint(2147483647) # make a seed with numpy generator 
        random.seed(seed) # apply this seed to img tranfsorms
        if self.transform is not None:
            img_gr = self.transform(img_gr)
        # else:
        #     img_gr = np.transpose(img_gr, axes=(2, 0, 1))
        #     img_gr = torch.from_numpy(img_gr).float()
        
        random.seed(seed) # apply this seed to target tranfsorms
        if self.target_transform is not None:
            img_gt = self.target_transform(img_gt)

        # # sanity check of the transforms
        # a = img_gr.numpy()*255
        # a = np.transpose(a, (1,2,0)).astype(np.uint8)
        # a = np.squeeze(a)
        # Image.fromarray(a).show()

        # b = img_gt.numpy()*255
        # b = np.transpose(b, (1,2,0)).astype(np.uint8)
        # b = np.squeeze(b)
        # Image.fromarray(b).show()
        # exit()

        return (img_gr, img_gt)


    def __len__(self):
        return len(self.X_train) # of how many examples(images?) you have


if __name__ == '__main__':
    # Define transforms (1)
    transformations = transforms.Compose([
        transforms.ToPILImage(mode='L'),
               transforms.RandomHorizontalFlip(), transforms.ToTensor()])

    transformations2 = transforms.Compose([
    transforms.ToPILImage(mode='L'),
            transforms.RandomHorizontalFlip(), transforms.ToTensor()])
    # Call the dataset
    # custom_dataset = MyCustomDataset(..., transformations)
    data_loader = DIBCODataset(transform=transformations, target_transform=transformations2, include_augmentation=True)
