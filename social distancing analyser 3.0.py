import time
import math
import cv2
import numpy as np
import os

confid = 0.5
thresh = 0.5
# vname=""
vname=input("Video name in videos folder (With Extension) :  ")

if(vname==""):
    vname="Town.mp4"
vid_path = "./videos/"+vname

if not os.path.isfile(vid_path):
    print("File not found..!!")
    os._exit(1)

angle_factor = 0.8
H_zoom_factor = 1.2
# Calibration needed for each video

def dist(c1, c2):
    return ((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2) ** 0.5

def T2S(T):
    S = abs(T/((1+T**2)**0.5))
    return S

def T2C(T):
    C = abs(1/((1+T**2)**0.5))
    return C

def isclose(p1,p2):

    c_d = dist(p1[2], p2[2])
    if(p1[1]<p2[1]):
        a_w = p1[0]
        a_h = p1[1]
    else:
        a_w = p2[0]
        a_h = p2[1]

    T = 0
    try:
        T=(p2[2][1]-p1[2][1])/(p2[2][0]-p1[2][0])
    except ZeroDivisionError:
        T = 1.633123935319537e+16
    S = T2S(T)
    C = T2C(T)
    d_hor = C*c_d
    d_ver = S*c_d
    vc_calib_hor = a_w*1.3
    vc_calib_ver = a_h*0.4*angle_factor
    c_calib_hor = a_w *1.7
    c_calib_ver = a_h*0.2*angle_factor
    # print(p1[2], p2[2],(vc_calib_hor,d_hor),(vc_calib_ver,d_ver))
    if (0<d_hor<vc_calib_hor and 0<d_ver<vc_calib_ver):
        return 1
    elif 0<d_hor<c_calib_hor and 0<d_ver<c_calib_ver:
        return 2
    else:
        return 0


labelsPath = "./coco.names"
LABELS = open(labelsPath).read().strip().split("\n")

np.random.seed(42)

weightsPath = "./yolov3.weights"
configPath = "./yolov3.cfg"

###### use this for faster processing (caution: slighly lower accuracy) ###########

#weightsPath = "./yolov3-tiny.weights"  
#configPath = "./yolov3-tiny.cfg"


net = cv2.dnn.readNetFromDarknet(configPath, weightsPath)
ln = net.getLayerNames()
ln = [ln[i[0] - 1] for i in net.getUnconnectedOutLayers()]
FR=0
vs = cv2.VideoCapture(vid_path)


#Counting total Frames present in given video
frameCnt = 0
print("Enter Gap Factor in range (1-4): \n1: Higest Accuracy, Slowest Speed ")
print("2: High Accuracy, Slow Speed \n3: High Accuracy, Better Speed \n4: Medium Accuracy, Max Speed ")
gapFactor = int(input("Enter Gap Factor (1 to 4) : "))
#gapFactor = 3    #number of frames gap to add to incease speed.

print("Counting total Frames present in this video")

while True:
    (grabbed, frame) = vs.read()

    if not grabbed:
        #end = time.time()
        break
    
    frameCnt = frameCnt + 1

    #if writer is None:
    #    fourcc = cv2.VideoWriter_fourcc(*"MP4V")
    #    writer = cv2.VideoWriter("op_"+vname, fourcc, 30, (frame.shape[1], frame.shape[0]), True)
    
    #writer.write(frame)

print("Total Frame Count is ", frameCnt)

vs = cv2.VideoCapture(vid_path)

counter = 0
# This counter is for counting each 

# vs = cv2.VideoCapture(0)  ## USe this if you want to use webcam feed
writer = None
(W, H) = (None, None)
oldlayer = None
timeForEach = 0  #calculates time requires to process one frame (depends upon processor used)
fl = 0
q = 0
while True:

    (grabbed, frame) = vs.read()
    if not grabbed:
        break

    counter = counter + 1


    #frame = cv2.resize(frame, (480,320))
    frame = cv2.resize(frame, (720,480))
    #frame = cv2.resize(frame, (720,480))
    if W is None or H is None:
        (H, W) = frame.shape[:2]
        FW=W
        if(W<1075):
            FW = 1075
        FR = np.zeros((H+210,FW,3), np.uint8)

        col = (255,255,255)
        FH = H + 210
    FR[:] = col

    #Processing Only Certain gap frames.

    if counter!=1 and counter%gapFactor!=0:
        frame = cv2.resize(frame, (720,480))
        #cv2.imshow('Social distancing analyser', frame)
        #cv2.waitKey(1)
        #print("Non-Processed Frame ",counter)
        #writer.write(frame)
        layerOutputs = oldlayer
        #continue
    if counter==1 or counter%gapFactor==0:
        #print("Working Frame ",counter)
        blob = cv2.dnn.blobFromImage(frame, 1 / 255.0, (416, 416), swapRB=True, crop=False)
        net.setInput(blob)
        start = time.time()
        layerOutputs = net.forward(ln)
        oldlayer = layerOutputs
        end = time.time()
        timeForEach = end-start

    boxes = []
    confidences = []
    classIDs = []

    for output in layerOutputs:

        for detection in output:

            scores = detection[5:]
            classID = np.argmax(scores)
            confidence = scores[classID]
            if LABELS[classID] == "person":

                if confidence > confid:
                    box = detection[0:4] * np.array([W, H, W, H])
                    (centerX, centerY, width, height) = box.astype("int")

                    x = int(centerX - (width / 2))
                    y = int(centerY - (height / 2))

                    boxes.append([x, y, int(width), int(height)])
                    confidences.append(float(confidence))
                    classIDs.append(classID)

    idxs = cv2.dnn.NMSBoxes(boxes, confidences, confid, thresh)

    if len(idxs) > 0:

        status = []
        idf = idxs.flatten()
        close_pair = []
        s_close_pair = []
        center = []
        co_info = []

        for i in idf:
            
            (x, y) = (boxes[i][0], boxes[i][1])
            (w, h) = (boxes[i][2], boxes[i][3])
            cen = [int(x + w / 2), int(y + h / 2)]
            center.append(cen)
            cv2.circle(frame, tuple(cen),1,(0,0,0),1)
            co_info.append([w, h, cen])

            status.append(0)
        for i in range(len(center)):
            for j in range(len(center)):
                g = isclose(co_info[i],co_info[j])

                if g == 1:

                    close_pair.append([center[i], center[j]])
                    status[i] = 1
                    status[j] = 1
                elif g == 2:
                    s_close_pair.append([center[i], center[j]])
                    if status[i] != 1:
                        status[i] = 2
                    if status[j] != 1:
                        status[j] = 2

        total_p = len(center)
        low_risk_p = status.count(2)
        high_risk_p = status.count(1)
        safe_p = status.count(0)
        kk = 0

        for i in idf:
            cv2.line(FR,(0,H+1),(FW,H+1),(0,0,0),2)
            cv2.putText(FR, "Social Distancing Analyser wrt. COVID-19", (210, H+60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            cv2.rectangle(FR, (20, H+80), (510, H+180), (100, 100, 100), 2)
            cv2.putText(FR, "Connecting lines shows closeness among people. ", (30, H+100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 0), 2)
            cv2.putText(FR, "-- YELLOW: CLOSE", (50, H+90+40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 170, 170), 2)
            cv2.putText(FR, "--    RED: VERY CLOSE", (50, H+40+110),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            # cv2.putText(frame, "--    PINK: Pathway for Calibration", (50, 150),
            #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180,105,255), 1)

            cv2.rectangle(FR, (535, H+80), (1060, H+140+40), (100, 100, 100), 2)
            cv2.putText(FR, "Bounding box shows the level of risk to the person.", (545, H+100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 0), 2)
            cv2.putText(FR, "-- DARK RED: HIGH RISK", (565, H+90+40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 150), 2)
            cv2.putText(FR, "--   ORANGE: LOW RISK", (565, H+150),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 120, 255), 2)

            cv2.putText(FR, "--    GREEN: SAFE", (565, H+170),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 150, 0), 2)

            
            tot_str = "TOTAL COUNT: " + str(total_p)
            high_str = "HIGH RISK COUNT: " + str(high_risk_p)
            low_str = "LOW RISK COUNT: " + str(low_risk_p)
            safe_str = "SAFE COUNT: " + str(safe_p)

            cv2.putText(FR, tot_str, (10, H +25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            cv2.putText(FR, safe_str, (200, H +25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 170, 0), 2)
            cv2.putText(FR, low_str, (380, H +25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 120, 255), 2)
            cv2.putText(FR, high_str, (630, H +25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 150), 2)

            (x, y) = (boxes[i][0], boxes[i][1])
            (w, h) = (boxes[i][2], boxes[i][3])
            if status[kk] == 1:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 150), 2)

            elif status[kk] == 0:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            else:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 120, 255), 2)

            kk += 1
        for h in close_pair:
            cv2.line(frame, tuple(h[0]), tuple(h[1]), (0, 0, 255), 2)
        for b in s_close_pair:
            cv2.line(frame, tuple(b[0]), tuple(b[1]), (0, 255, 255), 2)
        FR[0:H, 0:W] = frame
        frame = FR
        frame = cv2.resize(frame, (720,480))
        cv2.imshow('Social distancing analyser', frame)
        cv2.waitKey(1)

    if writer is None:
        fourcc = cv2.VideoWriter_fourcc(*"MP4V")
        frame = cv2.resize(frame, (720,480))
        writer = cv2.VideoWriter("op8_"+vname, fourcc, 30,
                                 (frame.shape[1], frame.shape[0]), True)
    frame = cv2.resize(frame, (720,480))
    #print("Saved Frame number is ",counter)
    completed = round(((counter*100)/frameCnt) , 2)
    time_sec = round((((frameCnt-counter)*timeForEach)/gapFactor),2)
    #print("Completed ",completed," % \Estimated time is = ",time_sec)
    print("Completed {0} % Estimated remaining time is = {1} Sec".format(completed,time_sec))
    writer.write(frame)
print("Processing finished: open"+"op_"+vname)
writer.release()
vs.release()
