import cv2
import mediapipe as mp
import numpy as np
import argparse
import time
import threading

# Parsowanie argumentów wiersza poleceń
# Parsowanie argumentów wiersza poleceń
parser = argparse.ArgumentParser(description='Licznik pompek')
parser.add_argument('--target', type=int, default=10, help='Docelowa liczba powtórzeń')
parser.add_argument('--rest-time', type=int, default=30, help='Czas przerwy między seriami (sekundy)')
parser.add_argument('--series', type=int, default=1, help='Liczba serii')
parser.add_argument('--prep-time', type=int, default=5, help='Czas przygotowania przed ćwiczeniem (sekundy)')

args = parser.parse_args()

target_pushups = args.target
rest_time = args.rest_time
total_series = args.series
prep_time = args.prep_time

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

# Funkcja do weryfikacji pompki
def verify_pushup(landmarks):
    # Pobierz współrzędne punktów ciała
    left_shoulder = [
        landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
        landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y
    ]
    left_elbow = [
        landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x,
        landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y
    ]
    left_wrist = [
        landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x,
        landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y
    ]
    
    right_shoulder = [
        landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x,
        landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y
    ]
    right_elbow = [
        landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x,
        landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y
    ]
    right_wrist = [
        landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].x,
        landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].y
    ]

    # Oblicz kąt w łokciach
    left_angle = calculate_angle(left_shoulder, left_elbow, left_wrist)
    right_angle = calculate_angle(right_shoulder, right_elbow, right_wrist)
    avg_angle = (left_angle + right_angle) / 2

    # Sprawdź, czy ciało jest w linii prostej (biodra w przybliżeniu na tej samej wysokości co ramiona)
    left_hip = [
        landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x,
        landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y
    ]
    right_hip = [
        landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x,
        landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y
    ]
    
    # Sprawdź różnicę wysokości między biodrami a ramionami
    body_alignment = abs((left_shoulder[1] + right_shoulder[1])/2 - (left_hip[1] + right_hip[1])/2)
    body_aligned = body_alignment < 0.1  # Tolerancja dla prostego ciała

    # Warunki dla poprawnej pompki
    if avg_angle < 90:  # Pozycja dolna
        pushup_success = True
    else:
        pushup_success = False

    # Sprawdź, czy ciało jest proste
    if not body_aligned:
        alignment_error = True
    else:
        alignment_error = False

    return pushup_success, avg_angle, alignment_error

# Główna pętla programu
cap = cv2.VideoCapture(0)  # Uruchom kamerę

# Zmienne do zliczania pompek
pushup_count = 0
pushup_position = False  # Czy jesteśmy w pozycji dolnej
min_angle_threshold = 90  # Minimalny kąt do uznania za dolną pozycję
max_angle_threshold = 160  # Maksymalny kąt do uznania za górną pozycję

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
                # Resetujemy licznik pompek na nową serię
                global pushup_count
                pushup_count = 0
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

    # Rysowanie landmarków na obrazie
    if results.pose_landmarks:
        mp_drawing.draw_landmarks(
            image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

        # Weryfikacja pompki
        pushup_success, angle, alignment_error = verify_pushup(results.pose_landmarks.landmark)

        # Logika zliczania pompek tylko w fazie ćwiczenia
        if exercise_state == "exercise":
            if pushup_success and angle < min_angle_threshold and not pushup_position:
                pushup_position = True  # Rozpoczęto ruch w dół
            elif pushup_position and angle > max_angle_threshold:
                pushup_position = False  # Zakończono ruch w górę
                pushup_count += 1  # Zwiększ licznik

        # Komunikaty - zawsze na górze sidebar_messages
        #if pushup_success:
            #sidebar_messages.insert(0, (f"Pushup OK! Angle: {angle:.2f}", (0, 255, 0)))
        #else:
        sidebar_messages.insert(0, (f"Adjust Pushup! Angle: {angle:.2f}", (0, 0, 255)))

       
        
        if pushup_count >= target_pushups and exercise_state == "exercise":
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
    cv2.putText(main_image, "POMPKI", (width + 90, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Dodajemy informacje do wyświetlenia w sidebarze
    # sidebar_messages = []  # USUNIĘTE, nie nadpisujemy komunikatów!
    
    # Stan ćwiczenia i liczniki
    if exercise_state == "prep":
        sidebar_messages.append((f"Przygotowanie: {remaining_prep_time}s", (255, 255, 0)))
    elif exercise_state == "exercise":
        sidebar_messages.append((f"Seria: {current_series}/{total_series}", (255, 255, 255)))
        sidebar_messages.append((f"Pompki: {pushup_count}/{target_pushups}", (0, 255, 0)))
    elif exercise_state == "rest":
        sidebar_messages.append((f"Przerwa: {remaining_time}s", (0, 255, 255)))
        sidebar_messages.append((f"Następna seria: {current_series}/{total_series}", (255, 255, 255)))
    elif exercise_state == "completed":
        sidebar_messages.append(("Ćwiczenie zakończone!", (0, 255, 0)))
    
    # Rysowanie panelu na napisy na oryginalnym obrazie
    if messages:
        panel_width, panel_height = 340, 170
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
    if 'alignment_error' in locals() and alignment_error:
        cv2.putText(main_image, "Błąd: Trzymaj ciało prosto", (width + 20, sidebar_y), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        sidebar_y += 40
    
    # Dodaj instrukcje
    cv2.putText(main_image, "Naciśnij 'q' aby zakończyć", (width + 20, height - 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

    cv2.imshow('Pushup Counter', main_image)

    # Przerwij pętlę po naciśnięciu klawisza 'q' lub zakończeniu wszystkich serii
    if cv2.waitKey(10) & 0xFF == ord('q') or exercise_state == "completed":
        break

# Zwolnienie zasobów
cap.release()
cv2.destroyAllWindows()