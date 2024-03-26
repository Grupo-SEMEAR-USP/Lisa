#!/usr/bin/env python3
import rospy
import cv2
from sensor_msgs.msg import Image
from std_msgs.msg import Float64MultiArray
from cv_bridge import CvBridge, CvBridgeError

# Def names and creating obj
nodeName = 'find_multifaces_node'
topicSubscribe = '/cam_image'

bridge = CvBridge()
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml') #classificador já pré treinado que eciste na biblioteca do open cv que identifica rostos
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml') #classificador já pré treinado que eciste na biblioteca do open cv que identifica olhos

def callbackfunc(message):
    frame = bridge.imgmsg_to_cv2(message) 
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) #convertendo a imagem para escala de cinza
    faces = face_cascade.detectMultiScale(gray, 1.3, 5) #retorna a localização das faces que aparecem na imagem
    for (x, y, w, h) in faces:
        face_found = frame[(y-20):(y + h + 20), (x-20):(x + w + 20)]
        send_face_image(face_found)
        send_face_position(x,y)
    
def send_face_image(face):
    msg = bridge.cv2_to_imgmsg(face,'bgr8')   

def send_face_position(x, y):
    position = Float64MultiArray()
    position.data = [x, y]

rospy.init_node(nodeName, anonymous=True)
rospy.loginfo("find_multifaces_node started")
rospy.Subscriber(topicSubscribe, Image, callbackfunc)
rospy.spin()

cv2.destroyAllWindows()