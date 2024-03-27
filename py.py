#!/usr/bin/python

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.metrics import accuracy_score
import warnings
import RPi.GPIO as GPIO
import spidev
import time
import requests

warnings.filterwarnings('ignore')

# Read the power.csv file
df = pd.read_csv('power.csv')

# Prepare the data for the machine learning model
x = df.drop(columns=['OUTPUT'])
y = df['OUTPUT']

# Split the data into training and testing sets
x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.1, random_state=2)

# Train the Naive Bayes model
NB = GaussianNB()
NB.fit(x_train, y_train)

# Set up SPI communication with the ADC
GPIO.setmode(GPIO.BCM)
spi = spidev.SpiDev()
spi.open(0, 0)

voltage_conversion_factor = 0.224828935
current_conversion_factor = 0.025

# Function to read SPI data from MCP3008 chip
def read_channel(channel):
    adc = spi.xfer2([1, (8 + channel) << 4, 0])
    data = ((adc[1] & 3) << 8) + adc[2]
    return data

totalvalue = 0

while True:
    # Read sensor data
    voltage_sensor = read_channel(0) * voltage_conversion_factor
    current_sensor = read_channel(1) * current_conversion_factor
    power = voltage_sensor * current_sensor
    unit = power / 1000
    totalvalue += unit

    # Predict using the machine learning model
    test_prediction = NB.predict([[voltage_sensor, current_sensor]])

    # Send sensor data to ThingSpeak
    params = {'field1': voltage_sensor, 'field2': current_sensor, 'field3': power, 'field4': totalvalue, 'key': '2UNTDA56FMZWU6KN'}
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
    
    try:
        response = requests.post("https://api.thingspeak.com/update", data=params, headers=headers)
        print(response.status_code, response.reason)
    except requests.exceptions.RequestException as e:
        print("Connection failed:", e)
        break

    print("Voltage\t      : {:.2f}".format(voltage_sensor))
    print("Current\t      : {:.2f}".format(current_sensor))
    print("Power\t      : {:.2f}".format(power))
    print("Unit Consumed : {:.2f}".format(totalvalue))
    print("Prediction\t: {}".format("High voltage" if test_prediction == 1 else "Low voltage"))
    print("\n")
    time.sleep(1)

# Clean up GPIO
GPIO.cleanup()
