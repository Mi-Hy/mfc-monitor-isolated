import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

def gpio4_high():
    GPIO.setup(4, GPIO.OUT)
    GPIO.output(4, GPIO.HIGH)

def gpio4_low():
    GPIO.output(4, GPIO.LOW)