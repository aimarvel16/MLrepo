#run with g37 kernel

import os
from datetime import datetime
import time
import threading
import json
from kafka import KafkaProducer
from kafka.errors import KafkaError
from sklearn.model_selection import train_test_split
import pandas as pd
import tensorflow_io as tfio
import tensorflow as tf

print("tensorflow-io version: {}".format(tfio.__version__))
print("tensorflow version: {}".format(tf.__version__))

x_train,y_train,x_test,y_test=""

def load_data():
    COLUMNS = [
          #  labels
           'class',
          #  low-level features
           'lepton_1_pT',
           'lepton_1_eta',
           'lepton_1_phi',
           'lepton_2_pT',
           'lepton_2_eta',
           'lepton_2_phi',
           'missing_energy_magnitude',
           'missing_energy_phi',
          #  high-level derived features
           'MET_rel',
           'axial_MET',
           'M_R',
           'M_TR_2',
           'R',
           'MT2',
           'S_R',
           'M_Delta_R',
           'dPhi_r_b',
           'cos(theta_r1)'
           ]
    susy_iterator = pd.read_csv('data/SUSY.csv.gz', header=None, names=COLUMNS, chunksize=100000)
    susy_df = next(susy_iterator)
    susy_df.head()

    train_df, test_df = train_test_split(susy_df, test_size=0.4, shuffle=True)
    print("Number of training samples: ",len(train_df))
    print("Number of testing sample: ",len(test_df))

    x_train_df = train_df.drop(["class"], axis=1)
    y_train_df = train_df["class"]

    x_test_df = test_df.drop(["class"], axis=1)
    y_test_df = test_df["class"]

    # The labels are set as the kafka message keys so as to store data
    # in multiple-partitions. Thus, enabling efficient data retrieval
    # using the consumer groups.
    x_train = list(filter(None, x_train_df.to_csv(index=False).split("\n")[1:]))
    y_train = list(filter(None, y_train_df.to_csv(index=False).split("\n")[1:]))

    x_test = list(filter(None, x_test_df.to_csv(index=False).split("\n")[1:]))
    y_test = list(filter(None, y_test_df.to_csv(index=False).split("\n")[1:]))

    NUM_COLUMNS = len(x_train_df.columns)

def write_to_kafka_in_producer():
    global x_train,y_train,x_test,y_test
    def error_callback(exc):
        raise Exception('Error while sendig data to kafka: {0}'.format(str(exc)))

    def write_to_kafka(topic_name, items):
        count=0
        producer = KafkaProducer(bootstrap_servers=['127.0.0.1:9092'])
        for message, key in items:
            producer.send(topic_name, key=key.encode('utf-8'), value=message.encode('utf-8')).add_errback(error_callback)
            count+=1
        producer.flush()
        print("Wrote {0} messages into topic: {1}".format(count, topic_name))

    write_to_kafka("susy-train", zip(x_train, y_train))
    write_to_kafka("susy-test", zip(x_test, y_test))


if __name__=="__main__":
    #load data
    load_data()

    #send data
    write_to_kafka_in_producer()
