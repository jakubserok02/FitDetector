import cv2
import mediapipe as mp
import math
import time
import threading
import numpy as np

# MediaPipe Pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()
mp_draw = mp.solutions.drawing_utils

# Pomocnicza funkcja - dystans między stopami
def get_feet_distance(landmarks):
    left = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value]
    right = landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value]
    return abs(left.x - right.x)

# Parametry
open_threshold = 0.2   # stopy szeroko - górna pozycja
close_threshold = 0.08 # stopy razem - dolna pozycja

import argparse

# Parsowanie argumentów wiersza poleceń
parser = argparse.ArgumentParser(description='Licznik pajacyków')
parser.add_argument('--target', type=int, default=10, help='Docelowa liczba powtórzeń')
parser.add_argument('--rest-time', type=int, default=30, help='Czas przerwy między seriami (sekundy)')
parser.add_argument('--series', type=int, default=1, help='Liczba serii')
parser.add_argument('--prep-time', type=int, default=5, help='Czas przygotowania przed ćwiczeniem (sekundy)')
args = parser.parse_args()

target_jumps = args.target
rest_time = args.rest_time
total_series = args.series
prep_time = args.prep_time

# Zmienne zliczania pajacyków
counter = 0
is_open = False

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
                # Resetujemy licznik na nową serię
                global counter
                counter = 0
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

cap = cv2.VideoCapture(0)

while True:
    success, frame = cap.read()
    if not success:
        break
        
    # Ustalamy wymiary obrazu dla layoutu
    height, width, _ = frame.shape
    
    # Tworzymy obraz sidebar dla informacji
    sidebar_width = 300
    main_image = np.zeros((height, width + sidebar_width, 3), dtype=np.uint8)
    
    # Kopiujemy oryginalny obraz na lewo
    main_image[:, :width] = frame

    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(image)
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    # Lista komunikatów do wyświetlenia
    messages = []
    sidebar_messages = []
    if results.pose_landmarks:
        mp_draw.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        landmarks = results.pose_landmarks.landmark

        # Usunięto stary kod liczenia powtórzeń, który powodował błąd

        # --- Nowy algorytm liczenia pajacyków ---
        # Sprawdź dystans między stopami (w pikselach)
        left_ankle = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE]
        right_ankle = landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE]
        h, w, _ = image.shape
        left_ankle_x = int(left_ankle.x * w)
        right_ankle_x = int(right_ankle.x * w)
        foot_dist = abs(left_ankle_x - right_ankle_x)

        # Sprawdź czy dłonie są powyżej barków
        left_wrist_y = landmarks[mp_pose.PoseLandmark.LEFT_WRIST].y
        right_wrist_y = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST].y
        left_shoulder_y = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].y
        right_shoulder_y = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER].y
        hands_above_shoulders = left_wrist_y < left_shoulder_y and right_wrist_y < right_shoulder_y

        # Progi - można dostosować
        open_threshold = 0.2  # im większa wartość, tym szerzej trzeba rozstawić nogi
        close_threshold = 0.18
        # Uwaga: wartości progów są w proporcji szerokości obrazu (0-1)

        # Liczenie powtórzeń
        if foot_dist / w > open_threshold and hands_above_shoulders:
            if not is_open:
                is_open = True
        else:
            if is_open and foot_dist / w < close_threshold:
                is_open = False
                counter += 1

        # Komunikaty do sidebaru
        if not "sidebar_messages" in locals():
            sidebar_messages = []
        sidebar_messages.append((f"Pajacyki: {counter}/{target_jumps}", (0, 255, 0)))
        if not hands_above_shoulders and is_open and exercise_state == "exercise":
            sidebar_messages.append(("Podnieś ręce wyżej!", (0, 140, 255)))
        if foot_dist / w <= open_threshold and exercise_state == "exercise":
            sidebar_messages.append(("Rozstaw szerzej nogi!", (0, 140, 255)))
        if counter >= target_jumps and exercise_state == "exercise":
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
    cv2.putText(main_image, "PAJACYKI", (width + 80, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Dodajemy informacje do wyświetlenia w sidebarze
    sidebar_messages = []
    
    # Stan ćwiczenia i liczniki
    if exercise_state == "prep":
        sidebar_messages.append((f"Przygotowanie: {remaining_prep_time}s", (255, 255, 0)))
    elif exercise_state == "exercise":
        sidebar_messages.append((f"Seria: {current_series}/{total_series}", (255, 255, 255)))
        sidebar_messages.append((f"Pajacyki: {counter}/{target_jumps}", (0, 255, 0)))
        if not hands_above_shoulders and is_open and exercise_state == "exercise":
            sidebar_messages.append(("Podnieś ręce wyżej!", (0, 140, 255)))
        if foot_dist / w <= open_threshold and exercise_state == "exercise":
            sidebar_messages.append(("Rozstaw szerzej nogi!", (0, 140, 255)))
    elif exercise_state == "rest":
        sidebar_messages.append((f"Przerwa: {remaining_time}s", (0, 255, 255)))
        sidebar_messages.append((f"Następna seria: {current_series}/{total_series}", (255, 255, 255)))
    elif exercise_state == "completed":
        sidebar_messages.append(("Ćwiczenie zakończone!", (0, 255, 0)))
    
    # Rysowanie panelu na napisy na oryginalnym obrazie
    if messages:
        panel_width, panel_height = 340, 140
        overlay = image.copy()
        cv2.rectangle(overlay, (5, 5), (5 + panel_width, 5 + panel_height), (0, 0, 0), -1)
        alpha = 0.6
        cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0, image)

    # Wyświetlanie komunikatów na panelu na oryginalnym obrazie
    y0 = 35
    for i, (msg, color) in enumerate(messages):
        y = y0 + i * 28
        cv2.putText(image, msg, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    # Kopiujemy obraz z landmarkami do głównego obrazu
    main_image[:, :width] = image
    
    # Wyświetlanie komunikatów na sidebarze
    y0 = 100
    for i, (msg, color) in enumerate(sidebar_messages):
        y = y0 + i * 40
        cv2.putText(main_image, msg, (width + 20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    # Dodaj instrukcje
    cv2.putText(main_image, "Naciśnij 'q' aby zakończyć", (width + 20, height - 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

    cv2.imshow("Jumping Jacks", main_image)
    if cv2.waitKey(10) & 0xFF == ord('q') or exercise_state == "completed":
        break

cap.release()
cv2.destroyAllWindows()
