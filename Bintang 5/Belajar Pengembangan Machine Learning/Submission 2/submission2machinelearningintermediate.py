# -*- coding: utf-8 -*-
"""Submission2MachineLearningIntermediate.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1DustMJUftNxUsVjHeN5FRn62Db6dZGkg

#Import dan Download Semua Package
"""

import os
import pandas as pd
import nltk, os, re, string
from keras.layers import Input, LSTM, Bidirectional, SpatialDropout1D, Dropout, Flatten, Dense, Embedding, BatchNormalization
from keras.models import Model
from keras.callbacks import EarlyStopping
from keras.preprocessing.text import Tokenizer, text_to_word_sequence
from keras.preprocessing.sequence import pad_sequences
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet as wn
from sklearn.model_selection import train_test_split
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
import matplotlib.pyplot as plt
import tensorflow as tf
from keras.preprocessing.sequence import TimeseriesGenerator
from sklearn.preprocessing import MinMaxScaler

"""#Fetch Dataset dari Kaggle"""

os.environ['KAGGLE_CONFIG_DIR'] = '/content'
!kaggle datasets download -d gpreda/covid-world-vaccination-progress

df = pd.read_csv('country_vaccinations.csv')
df.head(10)

"""#Daftar Nama Kolom"""

df.columns

"""#Daftar Negara"""

df.country.value_counts()

"""#Daftar Vaksin"""

df.vaccines.value_counts()

df_new = df.drop(columns=[
                          'iso_code', 'total_vaccinations', 'people_vaccinated', 
                          'people_fully_vaccinated', 'daily_vaccinations_raw', 
                          'daily_vaccinations', 'total_vaccinations_per_hundred', 
                          'people_vaccinated_per_hundred', 
                          'people_fully_vaccinated_per_hundred', 
                          'daily_vaccinations_per_million'
                          ])
df_new

"""#Total Data"""

df.shape

"""#Info Data"""

df.info()

"""#Memberikan Jumlah Kolom-Nilai yang Hilang"""

df.isnull().sum()

"""#Tabel Data Datetime"""

df['date']=pd.to_datetime(df['date'])
df['date'].head()
df['daily_vaccinations'].fillna(df['daily_vaccinations'].mean(), inplace=True) # we will fill the null row
df = df[['date','daily_vaccinations' ]]
df.head()

"""#Download wordnet dan stopwords"""

nltk.download('wordnet')
nltk.download('stopwords')

"""#Menghapus functuation"""

def cleaner(data):
    return(data.translate(str.maketrans('','', string.punctuation)))
    df_new.country = df_new.country.apply(lambda x: cleaner(x))
    df_new.date = df_new.date.apply(lambda x: lem(x))
    df_new.vaccines = df_new.vaccines.apply(lambda x: lem(x))
    df_new.source_name = df_new.source_name.apply(lambda x: lem(x))
    df_new.source_website = df_new.source_website.apply(lambda x: lem(x))

"""#Lematization"""

lemmatizer = WordNetLemmatizer()
def lem(data):
    pos_dict = {'N': wn.NOUN, 'V': wn.VERB, 'J': wn.ADJ, 'R': wn.ADV}
    return(' '.join([lemmatizer.lemmatize(w,pos_dict.get(t, wn.NOUN)) for w,t in nltk.pos_tag(data.split())]))
    df_new.country = df_new.country.apply(lambda x: lem(x))
    df_new.date = df_new.date.apply(lambda x: lem(x))
    df_new.vaccines = df_new.vaccines.apply(lambda x: lem(x))
    df_new.source_name = df_new.source_name.apply(lambda x: lem(x))
    df_new.source_website = df_new.source_website.apply(lambda x: lem(x))

"""#Menghapus Angka"""

def rem_numbers(data):
    return re.sub('[0-9]+','',data)
    df_new['country'].apply(rem_numbers)
    df_new['date'].apply(rem_numbers)
    df_new['vaccines'].apply(rem_numbers)
    df_new['source_name'].apply(rem_numbers)
    df_new['source_website'].apply(rem_numbers)

"""#Menghapus Stopword"""

st_words = stopwords.words()
def stopword(data):
    return(' '.join([w for w in data.split() if w not in st_words ]))
    df_new.country = df_new.country.apply(lambda x: stopword(x))
    df_new.date = df_new.date.apply(lambda x: lem(x))
    df_new.vaccines = df_new.vaccines.apply(lambda x: lem(x))
    df_new.source_name = df_new.source_name.apply(lambda x: lem(x))
    df_new.source_website = df_new.source_website.apply(lambda x: lem(x))

"""#Menampilkan Data Setelah Cleansing"""

df_new.head(10)

"""#Menampilkan Tabel untuk Model dan Plot (Time Series)"""

delhi=df[['date','daily_vaccinations']].copy()
delhi['just_date'] = delhi['date'].dt.date
delhifinal=delhi.drop('date',axis=1)
delhifinal.set_index('just_date', inplace= True)
delhifinal.head()

delhifinal.info()

plt.figure(figsize=(20,8))
plt.plot(delhifinal)
plt.title('Vaccine Statistics')
plt.xlabel('Date')
plt.ylabel('Daily Vaccinations')
plt.show()

date = df['date'].values
daily = df['daily_vaccinations'].values

def windowed_dataset(series, window_size, batch_size, shuffle_buffer):
    series = tf.expand_dims(series, axis=-1)
    ds = tf.data.Dataset.from_tensor_slices(series)
    ds = ds.window(window_size + 1, shift=1, drop_remainder=True)
    ds = ds.flat_map(lambda w: w.batch(window_size + 1))
    ds = ds.shuffle(shuffle_buffer)
    ds = ds.map(lambda w: (w[:-1], w[-1:]))
    return ds.batch(batch_size).prefetch(1)

"""#Split"""

x_train, x_test, y_train, y_test = train_test_split(date, daily, test_size = 0.2, random_state = 0 , shuffle=False)
print(len(x_train), len(x_test))

"""#Membangun Model menggunakan Model Sequential"""

scaler = MinMaxScaler()
train_scale = scaler.fit_transform(x_train.reshape(-1, 1))
test_scale = scaler.fit_transform(x_test.reshape(-1, 1))
look_back = 20
train_gen = TimeseriesGenerator(train_scale, train_scale, length=look_back, batch_size=20)
test_gen = TimeseriesGenerator(test_scale, test_scale, length=look_back, batch_size=1)
model = tf.keras.Sequential([
  tf.keras.layers.Conv1D(filters=312, kernel_size=5,
                      strides=1, padding="causal",
                      activation="relu",
                      input_shape=[None, 1]),
  tf.keras.layers.LSTM(128, return_sequences=True),
  tf.keras.layers.LSTM(120),
  tf.keras.layers.Dense(60, activation="softmax"),
  tf.keras.layers.Dense(20, activation="softmax"),
  tf.keras.layers.Dense(2),
  tf.keras.layers.Lambda(lambda x: x * 40)
])

lr_schedule = tf.keras.callbacks.LearningRateScheduler(
    lambda epoch: 1e-8 * 10**(epoch / 20))
optimizer = tf.keras.optimizers.SGD(lr=1e-8, momentum=0.9)
model.summary()

max = df['daily_vaccinations'].max()
print('Max value : ' )
print(max)

min = df['daily_vaccinations'].min()
print('Min Value : ')
print(min)

x = (1722328.0 - 0.0) * (10 / 100)
print(x)

"""#Implementasi Callback Apabila memenuhi Standar Akurasi yang Sudah Ditentukan"""

class myCallback(tf.keras.callbacks.Callback):
  def on_epoch_end(self, epoch, logs={}):
    if(logs.get('accuracy')>0.92 and logs.get('mae')<x):
      self.model.stop_training = True
      print("\nAkurasi pada training set dan validation set di atas 90% dan MAE < 10%")
callbacks = myCallback()

"""#Pelatihan Model"""

model.compile(loss=tf.keras.losses.Huber(),
              optimizer=optimizer,
              metrics=["accuracy", "mae"])
history = model.fit(train_gen, epochs=3, validation_data=test_gen, verbose=1, callbacks=[callbacks])

"""#Grafik MAE"""

plt.plot(history.history['mae'])
plt.plot(history.history['val_mae'])
plt.title('Grafik MAE')
plt.ylabel('Nilai MAE')
plt.xlabel('epoch')
plt.legend(['train', 'test'], loc='upper left')
plt.show()

"""#Grafik Akurasi"""

plt.plot(history.history['accuracy'])
plt.plot(history.history['val_accuracy'])
plt.title('Grafik Akurasi')
plt.ylabel('Nilai Akurasi')
plt.xlabel('epoch')
plt.legend(['train', 'test'], loc='upper left')
plt.show()

"""#Grafik Loss"""

plt.plot(history.history['loss'])
plt.plot(history.history['val_loss'])
plt.title('Grafik Loss')
plt.ylabel('Nilai Loss')
plt.xlabel('epoch')
plt.legend(['train', 'test'], loc='upper left')
plt.show()