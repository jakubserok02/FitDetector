import cv2
import mediapipe as mp
import numpy as np
import argparse
import time
import threading

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

# Parsowanie argumentów wiersza poleceń
parser = argparse.ArgumentParser(description='Licznik przysiadów')
parser.add_argument('--target', type=int, default=10, help='Docelowa liczba powtórzeń')
parser.add_argument('--rest-time', type=int, default=30, help='Czas przerwy między seriami (sekundy)')
parser.add_argument('--series', type=int, default=1, help='Liczba serii')
parser.add_argument('--prep-time', type=int, default=5, help='Czas przygotowania przed ćwiczeniem (sekundy)')

args = parser.parse_args()

target_squats = args.target
rest_time = args.rest_time
total_series = args.series
prep_time = args.prep_time

# Główna pętla programu
cap = cv2.VideoCapture(0)  # Uruchom kamerę

# Zmienne do zliczania przysiadów
squat_count = 0
squat_position = False  # Czy jesteśmy w pozycji przysiadu
min_angle_threshold = 90  # Minimalny kąt do uznania za pełny przysiad
max_angle_threshold = 160  # Maksymalny kąt do uznania za pozycję stojącą

# Zmienne do zarządzania stanem ćwiczenia
current_series = 1
timer_active = False
remaining_time = 0
exercise_state = "prep"  # Możliwe stany: prep, exercise, rest, completed
prep_timer_active = True
remaining_prep_time = prep_time

# Funkcja do aktualizacji timera odliczania
def update_timer():
    global remaining_time, timer_active, exercise_state, current_series, total_series
    
    if timer_active and remaining_time > 0:
        remaining_time -= 1
        threading.Timer(1.0, update_timer).start()
    elif timer_active and remaining_time <= 0:
        timer_active = False
        if exercise_state == "rest":
            current_series += 1
            if current_series <= total_series:
                exercise_state = "exercise"
                # Resetujemy licznik przysiadów na nową serię
                global squat_count
                squat_count = 0
            else:
                exercise_state = "completed"

# Funkcja do aktualizacji timera przygotowania
def update_prep_timer():
    global remaining_prep_time, prep_timer_active, exercise_state
    
    if prep_timer_active and remaining_prep_time > 0:
        remaining_prep_time -= 1
        threading.Timer(1.0, update_prep_timer).start()
    elif prep_timer_active and remaining_prep_time <= 0:
        prep_timer_active = False
        exercise_state = "exercise"

# Uruchomienie timera przygotowania
if prep_timer_active:
    threading.Timer(1.0, update_prep_timer).start()

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
        
    # Ustalamy wymiary obrazu dla layoutu
    height, width, _ = frame.shape
    
    # Tworzymy obraz sidebar dla informacji
    sidebar_width = 500
    main_image = np.zeros((height, width + sidebar_width, 3), dtype=np.uint8)
    
    # Kopiujemy oryginalny obraz na lewo
    main_image[:, :width] = frame

    # Konwersja obrazu na RGB
    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image.flags.writeable = False

    # Przetwarzanie obrazu za pomocą MediaPipe Pose
    results = pose.process(image)

    # Konwersja z powrotem na BGR
    image.flags.writeable = True
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    # Lista komunikatów do wyświetlenia
    messages = []
    sidebar_messages = []
    if results.pose_landmarks:
        mp_drawing.draw_landmarks(
            image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

        # Weryfikacja przysiadu
        squat_success, angle, knee_error, heel_error = verify_squat(results.pose_landmarks.landmark)

        # Logika zliczania przysiadów tylko w fazie ćwiczenia
        if exercise_state == "exercise":
            if squat_success and angle < min_angle_threshold and not squat_position:
                squat_position = True  # Rozpoczęto ruch w dół
            elif squat_position and angle > max_angle_threshold:
                squat_position = False  # Zakończono ruch w górę
                squat_count += 1  # Zwiększ licznik

        # Komunikaty tylko do sidebaru
        if squat_success:
            sidebar_messages.insert(0, (f"Squat OK! Angle: {angle:.2f}", (0, 255, 0)))
        else:
            sidebar_messages.insert(0, (f"Adjust Squat! Angle: {angle:.2f}", (0, 0, 255)))
        if knee_error:
            sidebar_messages.append(("Knee over toes! Keep your knee behind toes.", (0, 0, 255)))
        if heel_error:
            sidebar_messages.append(("Heel raised! Keep your heel down.", (0, 0, 255)))
        sidebar_messages.append((f"Przysiady: {squat_count}/{target_squats}", (255, 255, 255)))
        
        # Sprawdzenie czy cel został osiągnięty
        if squat_count >= target_squats and exercise_state == "exercise":
            sidebar_messages.append(("Cel osiagniety!", (0, 255, 0)))
            
            # Jeśli nie jest to ostatnia seria, przejdź do odliczania przerwy
            if current_series < total_series and not timer_active:
                exercise_state = "rest"
                remaining_time = rest_time
                timer_active = True
                threading.Timer(1.0, update_timer).start()
            elif current_series >= total_series:
                exercise_state = "completed"

    # Przygotowujemy sidebar
    cv2.rectangle(main_image, (width, 0), (width + sidebar_width, height), (40, 40, 40), -1)
    
    # Dodajemy sekcję nagłówkową w sidebarze
    cv2.rectangle(main_image, (width, 0), (width + sidebar_width, 60), (70, 70, 70), -1)
    cv2.putText(main_image, "PRZYSIAD", (width + 80, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Dodajemy informacje do wyświetlenia w sidebarze
    sidebar_messages = []
    
    # Stan ćwiczenia i liczniki
    if exercise_state == "prep":
        sidebar_messages.append((f"Przygotowanie: {remaining_prep_time}s", (255, 255, 0)))
    elif exercise_state == "exercise":
        sidebar_messages.append((f"Seria: {current_series}/{total_series}", (255, 255, 255)))
        sidebar_messages.append((f"Przysiady: {squat_count}/{target_squats}", (0, 255, 0)))
    elif exercise_state == "rest":
        sidebar_messages.append((f"Przerwa: {remaining_time}s", (0, 255, 255)))
        sidebar_messages.append((f"Następna seria: {current_series}/{total_series}", (255, 255, 255)))
    elif exercise_state == "completed":
        sidebar_messages.append(("Ćwiczenie zakończone!", (0, 255, 0)))
    
    # Rysowanie panelu na napisy na oryginalnym obrazie
    if messages:
        panel_width, panel_height = 340, 210
        overlay = image.copy()
        cv2.rectangle(overlay, (5, 5), (5 + panel_width, 5 + panel_height), (0, 0, 0), -1)
        alpha = 0.6
        cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0, image)

    # Wyświetlanie komunikatów na panelu na oryginalnym obrazie
    y0 = 35
    for i, (msg, color) in enumerate(messages):
        y = y0 + i * 40
        cv2.putText(image, msg, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    # Kopiujemy obraz z landmarkami do głównego obrazu
    main_image[:, :width] = image
    
    # Wyświetlanie komunikatów na sidebarze
    y0 = 100
    for i, (msg, color) in enumerate(sidebar_messages):
        y = y0 + i * 40
        cv2.putText(main_image, msg, (width + 20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    # Dodatkowe informacje o błędach do sidebara
    sidebar_y = 200
    if 'knee_error' in locals() and knee_error:
        cv2.putText(main_image, "Błąd: Kolano wychodzi", (width + 20, sidebar_y), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        sidebar_y += 40
        
    if 'heel_error' in locals() and heel_error:
        cv2.putText(main_image, "Błąd: Pięta uniesiona", (width + 20, sidebar_y), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        sidebar_y += 40
        
    # Dodaj instrukcje
    cv2.putText(main_image, "Naciśnij 'q' aby zakończyć", (width + 20, height - 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

    # Wyświetlanie obrazu
    cv2.imshow('Squat Counter', main_image)

    # Przerwij pętlę po naciśnięciu klawisza 'q' lub zakończeniu wszystkich serii
    if cv2.waitKey(10) & 0xFF == ord('q') or exercise_state == "completed":
        break

# Zwolnienie zasobów
cap.release()
cv2.destroyAllWindows()