""" 
Assessment_4_MohammadZahid
"""

#%%
# 1.import necessary packages
import numpy as np
import cv2, os, datetime
import pathlib
import matplotlib.pyplot as plt
from keras import layers
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.utils import plot_model
from tensorflow_examples.models.pix2pix import pix2pix
from tensorflow.keras import layers,optimizers,losses,metrics,callbacks,applications
from sklearn.model_selection import train_test_split
from IPython.display import clear_output

#%%
# 2.Data preparation
# 2.1 Prepare the path
#root_path = r"C:\Users\acer\Desktop\Assessment_4_MohammadZahid\dataset\data-science-bowl-2018-2\train"
data_path = r"C:\Users\acer\Desktop\Assessment_4_MohammadZahid\dataset\data-science-bowl-2018-2"
train_path = os.path.join(data_path,'train')
test_path = os.path.join(data_path,'test')

#2.2 Prepare empty list for train and test to hold the data
train_images = []
train_masks = []
test_images = []
test_masks = []

#2.3 Load the train images using opencv
train_image_dir = os.path.join(train_path,'inputs')
for image_file in os.listdir(train_image_dir):
    img = cv2.imread(os.path.join(train_image_dir,image_file))
    img = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
    img = cv2.resize(img,(128,128))
    train_images.append(img)

#2.4 Load the train masks
train_masks_dir = os.path.join(train_path,'masks')
for mask_file in os.listdir(train_masks_dir):
    mask = cv2.imread(os.path.join(train_masks_dir,mask_file),cv2.IMREAD_GRAYSCALE)
    mask = cv2.resize(mask,(128,128))
    train_masks.append(mask)

#2.5 Load the test images using opencv
test_image_dir = os.path.join(test_path,'inputs')
for image_file in os.listdir(test_image_dir):
    img = cv2.imread(os.path.join(test_image_dir,image_file))
    img = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
    img = cv2.resize(img,(128,128))
    test_images.append(img)

#2.6 Load the test masks
test_masks_dir = os.path.join(test_path,'masks')
for mask_file in os.listdir(test_masks_dir):
    mask = cv2.imread(os.path.join(test_masks_dir,mask_file),cv2.IMREAD_GRAYSCALE)
    mask = cv2.resize(mask,(128,128))
    test_masks.append(mask)

#%%
#2.7 Convert the train list of np array into a np array
train_images_np = np.array(train_images)
train_masks_np = np.array(train_masks)
#2.8 Convert the test list of np array into a np array
test_images_np = np.array(test_images)
test_masks_np = np.array(test_masks)

#%%
# 3. Data preprocessing
# 3.1 Expand the train mask dimension
train_masks_np_exp = np.expand_dims(train_masks_np,axis=-1)
# 3.1.1 check the train mask output
print(np.unique(train_masks_np_exp[0]))

# 3.2 Expand the test mask dimension
test_masks_np_exp = np.expand_dims(test_masks_np,axis=-1)
# 3.2.1 check the test mask output
print(np.unique(test_masks_np_exp[0]))

#%%
#3.3 Convert the train mask values from [0,255] into [0,1]
converted_train_masks = np.round(train_masks_np_exp / 255.0).astype(np.int64) #convert float to integer
# 3.3.1 Check the train mask output
print(np.unique(converted_train_masks[0]))

#3.4 Convert the test mask values from [0,255] into [0,1]
converted_test_masks = np.round(test_masks_np_exp / 255.0).astype(np.int64) #convert float to integer
# 3.4.1 Check the mask output
print(np.unique(converted_test_masks[0]))

#%%
# 3.5 Normalize the train images
converted_train_images = train_images_np/ 255.0

# 3.6 Normalize the test images
converted_test_images = test_images_np/ 255.0

#%%
# 4. Perform train-test split
SEED = 42
X_train,X_test,y_train,y_test = train_test_split(converted_train_images,converted_train_masks,test_size=0.2,random_state=SEED)

#%%
# 5. Convert the numpy arrays into tensor slices
X_train_tensor = tf.data.Dataset.from_tensor_slices(X_train)
X_test_tensor = tf.data.Dataset.from_tensor_slices(X_test)
y_train_tensor = tf.data.Dataset.from_tensor_slices(y_train)
y_test_tensor = tf.data.Dataset.from_tensor_slices(y_test)

#%%
# 6.Combine the images and masks using the zip method
train_dataset = tf.data.Dataset.zip((X_train_tensor,y_train_tensor))
test_dataset = tf.data.Dataset.zip((X_test_tensor,y_test_tensor))

#%%
# 7. define data augmentation pipeline as a single layer through subclassing
class Augment(keras.layers.Layer):
    def __init__(self,seed=42):
        super().__init__()
        self.augment_inputs = keras.layers.RandomFlip(mode='horizontal',seed=seed)
        self.augment_labels = keras.layers.RandomFlip(mode='horizontal',seed=seed)

    def call(self,inputs,labels):
        inputs = self.augment_inputs(inputs)
        labels = self.augment_labels(labels)
        return inputs, labels

# 8. Build the dataset
# 8.1 define parameters

BATCH_SIZE = 16
AUTOTUNE = tf.data.AUTOTUNE
BUFFER_SIZE = 1000
TRAIN_SIZE = len(train_dataset)
STEPS_PER_EPOCH = TRAIN_SIZE//BATCH_SIZE

train_batches = (
    train_dataset
    .cache()
    .shuffle(BUFFER_SIZE)
    .batch(BATCH_SIZE)
    .repeat()
    .map(Augment())
    .prefetch(buffer_size=tf.data.AUTOTUNE)
)
test_batches = test_dataset.batch(BATCH_SIZE)

#%%
# 9. Visualize some pictures as example
def display(display_list):
    plt.figure(figsize=(15,15))
    title = ['Input Image','True Mask','Predicted Mask']
    for i in range(len(display_list)):
        plt.subplot(1,len(display_list),i+1)
        plt.title(title[i])
        plt.imshow(keras.utils.array_to_img(display_list[i]))
    plt.show()
for images,masks in train_batches.take(2):
    sample_image,sample_mask = images[0],masks[0]
    display([sample_image,sample_mask])

#%%
# 10. Model development
# 10.1 Use a pretrained model as the feature extractor
base_model = keras.applications.MobileNetV2(input_shape=[128,128,3],include_top=False)
base_model.summary()

# 10.2 use these activation layers as the outputs from the feature extractor (some of these outputs will be used to perform concatenation at the upsampling path)
layer_names = [
    'block_1_expand_relu', #64x64
    'block_3_expand_relu',  #32x32
    'block_6_expand_relu',  #16x16
    'block_13_expand_relu', #8x8
    'block_16_project',     #4x4
]
base_model_outputs = [base_model.get_layer(name).output for name in layer_names]

# 10.3 Instantiate the feature extractor
down_stack = keras.Model(inputs=base_model.input,outputs=base_model_outputs)
down_stack.trainable = False

# 10.4 Define the upsampling path
up_stack = [
    pix2pix.upsample(512,3),    #4x4 --> 8x8
    pix2pix.upsample(256,3),    #8x8 --> 16x16
    pix2pix.upsample(124,3),    #16x16 --> 32x32
    pix2pix.upsample(64,3),     #32x32 --> 64x64
]
OUTPUT_CLASSES = 3

# 10.5 use functional API to construct the entire U-net
def unet(output_channels:int):
    inputs = keras.layers.Input(shape=[128,128,3])
    #Downsample through the model
    skips = down_stack(inputs)
    x = skips[-1]
    skips = reversed(skips[:-1])

    #Build the upsampling path and establish the concatenation
    for up, skip in zip(up_stack,skips):
        x = up(x)
        concat = keras.layers.Concatenate()
        x = concat([x,skip])

    #use a transpose convolution layer to perform the last upsampling, this will become the output layer
    last = keras.layers.Conv2DTranspose(filters=output_channels,kernel_size=3,strides=2,padding='same') #64x64 --> 128x128
    outputs = last(x)

    model = keras.Model(inputs=inputs,outputs=outputs)
    return model

# %%
# 11. Use the function to create the model
OUTPUT_CHANNELS = 3
model = unet(OUTPUT_CHANNELS)
model.summary()
keras.utils.plot_model(model)

#%%
# 12. Compile the model
loss = keras.losses.SparseCategoricalCrossentropy(from_logits=True)
model.compile(optimizer='adam',loss=loss,metrics=['accuracy'])

#%%
# 13. Create functions to show predictions
def create_mask(pred_mask):
    pred_mask = tf.argmax(pred_mask,axis=-1)
    pred_mask = pred_mask[...,tf.newaxis]
    return pred_mask[0]

def show_predictions(dataset=None,num=1):
    if dataset:
        for image,mask in dataset.take(num):
            pred_mask = model.predict(image)
            display([image[0],mask[0],
            create_mask(pred_mask)])
    else:
        display([sample_image,sample_mask,create_mask(model.predict(sample_image[tf.newaxis,...]))])
show_predictions()

#%%
# 14. Create a callback function to make use of the show_predictions function
# specify callbacks TensorBoard 
log_path = os.path.join('log_dir','assessment_4',datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
tb = callbacks.TensorBoard(log_dir=log_path)
es = callbacks.EarlyStopping(monitor='loss', patience=5,restore_best_weights=True,verbose=1)
rlr = callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.1,patience=2, min_lr=0.0001)

#%%
# 15. model training
EPOCHS = 10
model_history = model.fit(train_batches,epochs=EPOCHS,steps_per_epoch=STEPS_PER_EPOCH,validation_data=test_batches,callbacks=[tb,es,rlr])

#%%
# 16. Model deployment
show_predictions(test_batches,3)
loss = model_history.history["loss"]
val_loss = model_history.history['val_loss']

plt.figure()
plt.plot(model_history.epoch, loss, 'r', label = 'Training loss')
plt.plot(model_history.epoch, val_loss, 'b', label = 'Validation loss')
plt.title('Training and Validation Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss Value')
plt.ylim([0,1])
plt.legend()
plt.savefig('Loss.png')
plt.show()

acc = model_history.history['accuracy']
val_acc = model_history.history['val_accuracy']

plt.figure()
plt.plot(model_history.epoch, acc, 'r', label='Training acc')
plt.plot(model_history.epoch, val_acc, 'b', label='Validation acc')
plt.title('Training and Validation acc')
plt.xlabel('Epoch')
plt.ylabel('Acc Value')
plt.ylim([0.5, 1])
plt.legend()
plt.savefig('Accuracy.png')
plt.show()

# 16.1 plot model architecture and save image
plot_model(model, show_shapes=True, show_layer_names=True)

# 16.2 save model
model.save('saved_models/model.h5',include_optimizer=False)

#%%
# 17. predicting model
X_test_true_tensor = tf.data.Dataset.from_tensor_slices(converted_test_images)
y_test_true_tensor = tf.data.Dataset.from_tensor_slices(converted_test_masks)
true_test_dataset = tf.data.Dataset.zip((X_test_true_tensor,y_test_true_tensor))
true_test_batches = test_dataset.batch(BATCH_SIZE)
model.evaluate(true_test_batches)
show_predictions(true_test_batches,num=2)

#%%