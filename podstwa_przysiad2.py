import cv2
import mediapipe as mp
import numpy as np

# Inicjalizacja MediaPipe Pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils

# Funkcja do obliczania kąta między trzema punktami
def calculate_angle(a, b, c):
    a = np.array(a)  # Pierwszy punkt
    b = np.array(b)  # Środkowy punkt
    c = np.array(c)  # Ostatni punkt

    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)

    if angle > 180.0:
        angle = 360 - angle

    return angle

# Funkcja do weryfikacji ćwiczenia (np. przysiad)
def verify_squat(landmarks):
    # Pobierz współrzędne punktów ciała
    left_hip = [
        landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x,
        landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y
    ]
    left_knee = [
        landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x,
        landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y
    ]
    left_ankle = [
        landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x,
        landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y
    ]
    left_heel = [
        landmarks[mp_pose.PoseLandmark.LEFT_HEEL.value].x,
        landmarks[mp_pose.PoseLandmark.LEFT_HEEL.value].y
    ]
    left_foot_index = [
        landmarks[mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value].x,
        landmarks[mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value].y
    ]

    # Oblicz kąt w kolanie
    angle = calculate_angle(left_hip, left_knee, left_ankle)

    # Sprawdź, czy kolano wychodzi poza linię palców
    knee_over_toes = left_knee[0] > left_foot_index[0]  # Porównaj współrzędne x
    knee_over_toes_distance = abs(left_knee[0] - left_foot_index[0])  # Odległość kolana od palców

    # Sprawdź, czy pięta jest podniesiona wyżej niż palce
    heel_raised = left_heel[1] < left_foot_index[1]  # Porównaj współrzędne y
    heel_raised_distance = abs(left_heel[1] - left_foot_index[1])  # Odległość pięty od palców

    # Progi tolerancji (można dostosować)
    knee_tolerance = 0.03  # Tolerancja dla kolana (5% szerokości obrazu)
    heel_tolerance = 0.02  # Tolerancja dla pięty (3% wysokości obrazu)

    # Sprawdź, czy kąt jest w zakresie przysiadu
    if angle < 120:  # Przykładowy warunek dla przysiadu
        squat_success = True
    else:
        squat_success = False

    # Sprawdź, czy kolano wychodzi poza linię palców (z tolerancją)
    if knee_over_toes and knee_over_toes_distance > knee_tolerance:
        knee_error = True
    else:
        knee_error = False

    # Sprawdź, czy pięta jest podniesiona (z tolerancją)
    if heel_raised and heel_raised_distance > heel_tolerance:
        heel_error = True
    else:
        heel_error = False

    return squat_success, angle, knee_error, heel_error

# Główna pętla programu
cap = cv2.VideoCapture(0)  # Uruchom kamerę

# Zmienne do zliczania przysiadów
squat_count = 0
squat_position = False  # Czy jesteśmy w pozycji przysiadu
min_angle_threshold = 90  # Minimalny kąt do uznania za pełny przysiad
max_angle_threshold = 160  # Maksymalny kąt do uznania za pozycję stojącą

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Konwersja obrazu na RGB
    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image.flags.writeable = False

    # Przetwarzanie obrazu za pomocą MediaPipe Pose
    results = pose.process(image)

    # Konwersja z powrotem na BGR
    image.flags.writeable = True
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    # Rysowanie landmarków na obrazie
    if results.pose_landmarks:
        mp_drawing.draw_landmarks(
            image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

        # Weryfikacja przysiadu
        squat_success, angle, knee_error, heel_error = verify_squat(results.pose_landmarks.landmark)

        # Logika zliczania przysiadów
        if squat_success and angle < min_angle_threshold and not squat_position:
            squat_position = True  # Rozpoczęto przysiad
        elif squat_position and angle > max_angle_threshold:
            squat_position = False  # Zakończono przysiad
            squat_count += 1  # Zwiększ licznik

        # Wyświetlanie informacji o przysiadzie
        if squat_success:
            cv2.putText(image, f"Squat OK! Angle: {angle:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        else:
            cv2.putText(image, f"Adjust Squat! Angle: {angle:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Wyświetlanie informacji o kolanie
        if knee_error:
            cv2.putText(image, "Knee over toes! Keep your knee behind toes.", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Wyświetlanie informacji o pięcie
        if heel_error:
            cv2.putText(image, "Heel raised! Keep your heel down.", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        # Wyświetlanie liczby przysiadów
        cv2.putText(image, f"Squats: {squat_count}", (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    # Wyświetlanie obrazu
    cv2.imshow('Squat Counter', image)

    # Przerwij pętlę po naciśnięciu klawisza 'q'
    if cv2.waitKey(10) & 0xFF == ord('q'):
        break

# Zwolnienie zasobów
cap.release()
cv2.destroyAllWindows()