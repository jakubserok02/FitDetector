import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import time
import threading
import subprocess
import sys
import os

class ExerciseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Aplikacja do Ćwiczeń")
        self.root.geometry("520x630")
        
        # Style
        style = ttk.Style()
        style.configure('TButton', font=('Helvetica', 13, 'bold'), padding=8)
        style.configure('TLabel', font=('Helvetica', 13))
        style.configure('Header.TLabel', font=('Helvetica', 20, 'bold'))
        
        # Variables
        self.exercises = ["Pompki", "Przysiady", "Pajacyki"]
        self.selected_exercise = tk.StringVar(value=self.exercises[0])
        self.reps = tk.IntVar(value=10)
        self.series = tk.IntVar(value=1)
        self.rest_time = tk.IntVar(value=30)  # w sekundach
        self.prep_time = tk.IntVar(value=5)   # czas oczekiwania przed startem (domyślnie 5s)
        self.current_series = 0
        self.is_running = False
        self.process = None
        self.timer_id = None
        self.remaining_rest_time = 0
        self.in_rest_period = False
        self.exercise_start_time = 0
        self.prep_timer_id = None
        self.remaining_prep_time = 0
        
        # Create UI
        self.create_widgets()
    
    def create_widgets(self):
        # Header
        header = ttk.Label(
            self.root,
            text="Trening Siłowy - Konfiguracja",
            style='Header.TLabel',
            anchor='center'
        )
        header.pack(pady=(18, 8), padx=10, fill="x")
        
        # Exercise selection
        exercise_frame = ttk.LabelFrame(self.root, text="Wybierz ćwiczenie", padding=6)
        exercise_frame.pack(pady=(2,6), padx=16, fill="x")
        
        for exercise in self.exercises:
            rb = ttk.Radiobutton(
                exercise_frame,
                text=exercise,
                variable=self.selected_exercise,
                value=exercise
            )
            rb.pack(anchor="w", pady=2, padx=4)
        
        # Repetitions
        reps_frame = ttk.LabelFrame(self.root, text="Liczba powtórzeń w serii", padding=6)
        reps_frame.pack(pady=(2,6), padx=16, fill="x")
        
        reps_scale = ttk.Scale(
            reps_frame,
            from_=1,
            to=50,
            orient="horizontal",
            variable=self.reps,
            command=lambda x: self.update_reps_label(),
            length=320
        )
        reps_scale.pack(fill="x", padx=8, pady=2)
        
        self.reps_label = ttk.Label(reps_frame, text=f"{self.reps.get()} powtórzeń", font=('Helvetica', 13, 'bold'))
        self.reps_label.pack(pady=(0,2))
        
        # Series
        series_frame = ttk.LabelFrame(self.root, text="Liczba serii", padding=6)
        series_frame.pack(pady=(2,6), padx=16, fill="x")
        
        series_scale = ttk.Scale(
            series_frame,
            from_=1,
            to=10,
            orient="horizontal",
            variable=self.series,
            command=lambda x: self.update_series_label(),
            length=320
        )
        series_scale.pack(fill="x", padx=8, pady=2)
        
        self.series_label = ttk.Label(series_frame, text=f"{self.series.get()} serii", font=('Helvetica', 13, 'bold'))
        self.series_label.pack(pady=(0,2))
        
        # Rest time
        rest_frame = ttk.LabelFrame(self.root, text="Czas przerwy między seriami (sekundy)", padding=6)
        rest_frame.pack(pady=(2,6), padx=16, fill="x")
        
        rest_scale = ttk.Scale(
            rest_frame,
            from_=10,
            to=180,
            orient="horizontal",
            variable=self.rest_time,
            command=lambda x: self.update_rest_label(),
            length=320
        )
        rest_scale.pack(fill="x", padx=8, pady=1)  # Mniejsze pady
        
        self.rest_label = ttk.Label(rest_frame, text=f"{self.rest_time.get()} sekund przerwy", font=('Helvetica', 15, 'bold'))
        self.rest_label.pack(pady=(0,1))  # Mniejsze pady

        # Preparation time before exercise
        prep_frame = ttk.LabelFrame(self.root, text="Czas przygotowania przed startem (sekundy)", padding=6)
        prep_frame.pack(pady=(2,10), padx=16, fill="x")
        
        prep_scale = ttk.Scale(
            prep_frame,
            from_=0,
            to=20,
            orient="horizontal",
            variable=self.prep_time,
            command=lambda x: self.update_prep_label(),
            length=320
        )
        prep_scale.pack(fill="x", padx=8, pady=2)
        
        self.prep_label = ttk.Label(prep_frame, text=f"{self.prep_time.get()} sekund przygotowania", font=('Helvetica', 15, 'bold'))
        self.prep_label.pack(pady=(0,2))
        
        # Status label
        self.status_label = ttk.Label(self.root, text="Gotowy do rozpoczęcia", font=('Helvetica', 16, 'bold'), anchor='center')
        self.status_label.pack(pady=(10, 8), padx=10, fill="x")
        
        # Start button
        self.start_button = ttk.Button(
            self.root,
            text="Rozpocznij trening",
            command=self.start_exercise
        )
        self.start_button.pack(pady=(5, 7), padx=60, fill="x")
        
        # Stop button (initially hidden)
        self.stop_button = ttk.Button(
            self.root,
            text="Zatrzymaj trening",
            command=self.stop_exercise,
            state='disabled'
        )
        self.stop_button.pack(pady=(0, 7), padx=60, fill="x")

        # Label na podsumowanie kalorii
        self.summary_label = ttk.Label(self.root, text="", font=('Helvetica', 13, 'bold'), anchor='center')
        self.summary_label.pack(pady=(10, 6), padx=10, fill="x")
    
    def update_reps_label(self):
        self.reps_label.config(text=f"{self.reps.get()} powtórzeń")
        
    def update_series_label(self):
        self.series_label.config(text=f"{self.series.get()} serii")
        
    def update_rest_label(self):
        mins = self.rest_time.get() // 60
        secs = self.rest_time.get() % 60
        self.rest_label.config(text=f"{mins:02d}:{secs:02d} min przerwy")
    
    def update_prep_label(self):
        self.prep_label.config(text=f"{self.prep_time.get()} sekund przygotowania")
    
    def start_exercise(self):
        # Resetowanie UI
        self.stop_exercise()
        self.is_running = True
        
        # Przygotowywanie parametrów
        self.exercise = self.selected_exercise.get()
        self.reps_count = self.reps.get()
        self.series_count = self.series.get()
        self.rest_time_count = self.rest_time.get()
        self.current_series = 1
        self.exercise_start_time = time.time()
        
        # Aktualizacja UI
        self.status_label.config(text=f"Wykonywanie: {self.exercise}", foreground='blue')
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        if hasattr(self, 'summary_label'):
            self.summary_label.config(text="")
        
        # Rozpoczęcie ćwiczenia bezpośrednio - wszystkimi seriami zarządza skrypt ćwiczenia
        threading.Thread(target=self.run_exercise, args=(self.exercise, self.reps_count, True), daemon=True).start()
    
    # Funkcja usunięta - odliczanie jest teraz w skryptach ćwiczeń
    
    # Funkcja usunięta - zarządzanie seriami jest teraz w skryptach ćwiczeń
    
    # Funkcja usunięta - zarządzanie UI dla serii jest teraz w skryptach ćwiczeń
    
    def start_rest_period(self):
        # Ta funkcja jest wywoływana po zakończeniu ćwiczenia w skrypcie
        # ale nie będzie już używana do uruchamiania nowych serii - skrypt ćwiczenia obsługuje to sam
        
        if not self.is_running:
            return
            
        # Przechodzimy od razu do zakończenia ćwiczenia po powrocie ze skryptu
        self.exercise_complete()
    
    # Funkcja usunięta - odliczanie przerwy jest teraz w skryptach ćwiczeń
    
    # Funkcja usunięta - zarządzanie UI dla przerwy jest teraz w skryptach ćwiczeń
    
    def stop_exercise(self):
        self.is_running = False
        self.in_rest_period = False
        if hasattr(self, 'timer_id') and self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        if hasattr(self, 'prep_timer_id') and self.prep_timer_id:
            self.root.after_cancel(self.prep_timer_id)
            self.prep_timer_id = None
        self.reset_ui()
        self.status_label.config(text="Trening zatrzymany", foreground='red')
        if hasattr(self, 'summary_label'):
            self.summary_label.config(text="Trening został przerwany.", foreground='red')
    
    def run_exercise(self, exercise, reps, is_last_series):
        try:
            # Mapowanie ćwiczeń do odpowiednich skryptów
            exercise_map = {
                "Pompki": "pushup.py",
                "Przysiady": "przysiad.py",
                "Pajacyki": "jumpingjacks.py"
            }
            
            script_name = exercise_map.get(exercise)
            if not script_name or not os.path.exists(script_name):
                raise FileNotFoundError(f"Nie znaleziono skryptu dla ćwiczenia: {exercise}")
            
            # Uruchomienie odpowiedniego skryptu ze wszystkimi parametrami
            self.process = subprocess.Popen([
                sys.executable, 
                script_name, 
                "--target", str(reps),
                "--series", str(self.series.get()),
                "--rest-time", str(self.rest_time.get()),
                "--prep-time", str(self.prep_time.get())
            ])
            
            # Oczekiwanie na zakończenie ćwiczenia
            while self.process.poll() is None and self.is_running:
                time.sleep(0.1)
                
            if self.process.returncode != 0 and self.is_running:
                error_msg = f"Błąd podczas wykonywania ćwiczenia. Kod błędu: {self.process.returncode}"
                self.root.after(0, lambda msg=error_msg: messagebox.showerror("Błąd", msg))
                return
                
            if self.is_running:
                # Wszystkie serie już zostały wykonane w oknie ćwiczenia
                self.root.after(0, self.exercise_complete)
                
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda msg=error_msg: messagebox.showerror("Błąd", msg))
        finally:
            if hasattr(self, 'process') and self.process:
                self.process.terminate()
                self.process = None
    
    def update_counter(self, count, exercise):
        self.start_button.config(text=f"{exercise}: {count}...")
    
    def exercise_complete(self):
        # Oblicz kalorie
        calories_per_rep = {
            "Pompki": 0.5,
            "Przysiady": 0.32,
            "Pajacyki": 0.2
        }
        exercise = getattr(self, 'exercise', self.selected_exercise.get())
        reps = getattr(self, 'reps_count', self.reps.get())
        series = getattr(self, 'series_count', self.series.get())
        kcal = calories_per_rep.get(exercise, 0.3) * reps * series
        summary = f"Trening zakończony pomyślnie!\nSpalone kalorie: {kcal:.1f} kcal"
        self.status_label.config(text="Trening zakończony!", foreground='green')
        if hasattr(self, 'summary_label'):
            self.summary_label.config(text=summary, foreground='purple')
        self.root.after(300, lambda: messagebox.showinfo("Sukces", summary))
        self.reset_ui()
    
    def reset_ui(self):
        self.is_running = False
        self.in_rest_period = False
        self.current_series = 0
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        # NIE czyść summary_label tutaj, aby podsumowanie pozostało po zakończeniu treningu
        if hasattr(self, 'process') and self.process:
            self.process.terminate()
            self.process = None
        if hasattr(self, 'timer_id') and self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        if hasattr(self, 'prep_timer_id') and self.prep_timer_id:
            self.root.after_cancel(self.prep_timer_id)
            self.prep_timer_id = None

def main():
    root = tk.Tk()
    app = ExerciseApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()