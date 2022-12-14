import cv2
import mediapipe as mp

"""def getFace(frame):
	mp_facemesh = mp.solutions.face_mesh
	face_Images = mp_facemesh.FaceMesh(static_image_mode = True, max_num_faces = 1)
	frame = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
	frame.flags.writeable = False
	results = face_Images.process(frame)
	frame.flags.writeable = True
	
	if results.multi_face_landmarks:
		print("face detected")
	else:
		print("No face detected") 
"""
print("Hello World")
vid = cv2.VideoCapture(0)
while True:
	rec, frame = vid.read()
	#getFace(frame)
	cv2.imshow("frame", frame)
	key = cv2.waitKey(1)
	if key == 27:
		break
