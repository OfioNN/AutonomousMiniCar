import cv2
import requests
import time


# Stream z ESP32-CAM
url = '***'
cap = cv2.VideoCapture(url)

# Adres ESP32 sterującego ruchem
esp32_control_url = '***'

# Model detekcji
net = cv2.dnn.readNetFromCaffe(
    '***',
    '***'
)

CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
           "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
           "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
           "sofa", "train", "tvmonitor"]

# last_command = None
last_command_time = 0
command_interval = 0.2  # minimalny odstęp w sekundach


while True:
    ret, frame = cap.read()
    if not ret:
        print("Brak klatki.")
        break

    (h, w) = frame.shape[:2]
    center_x_frame = w // 2

    # Przygotuj blob i wykonaj detekcję
    blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)),
                                 0.007843, (300, 300), 127.5)
    net.setInput(blob)
    detections = net.forward()

    person_detected = False
    command = "stop"

    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > 0.5:
            idx = int(detections[0, 0, i, 1])
            label = CLASSES[idx]

            if label == "person":
                person_detected = True
                box = detections[0, 0, i, 3:7] * [w, h, w, h]
                (startX, startY, endX, endY) = box.astype("int")

                person_center_x = (startX + endX) // 2
                person_width = endX - startX

                center_tolerance = 100
                distance_too_close = 320
                distance_too_far = 120

                if person_center_x < center_x_frame - center_tolerance:
                    command = "right"  # osoba po lewej -> skręć W PRAWO (z punktu widzenia kamery)
                elif person_center_x > center_x_frame + center_tolerance:
                    command = "left"   # osoba po prawej -> skręć W LEWO (z punktu widzenia kamery)

                else:
                    # Osoba wycentrowana – reguluj odległość
                    if person_width > distance_too_close:
                        command = "back"
                    elif person_width < distance_too_far:
                        command = "forward"
                    else:
                        command = "stop"

                # Wizualizacja
                color = (0, 255, 0)
                cv2.rectangle(frame, (startX, startY), (endX, endY), color, 2)
                cv2.putText(frame, f"{label} {confidence:.2f}",
                            (startX, startY - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                            color, 2)
                break
 
    current_time = time.time()
    if person_detected and (current_time - last_command_time) >= command_interval:
        try:
            requests.get(f"{esp32_control_url}/{command}")
            print(f"Komenda: {command}")
            last_command = command
            last_command_time = current_time
        except:
            print("Błąd wysyłania komendy.")



    cv2.imshow("Detekcja osoby", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
