import cv2
import mediapipe as mp
import math
import numpy as np
import time
from datetime import datetime

# ================== GLOBAL SETTINGS ==================
SCAN_DURATION = 5  # seconds
scan_start_time = None
scores_buffer = []
final_score = None
final_ratios = None
state = "IDLE"  # IDLE, SCANNING, RESULT
mode = "Aesthetic"

# ================== MEDIAPIPE INIT ==================
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True
)

# ================== HELPER FUNCTIONS ==================
def distance(p1, p2):
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

def outlined_text(img, text, pos, color, scale=0.7, thickness=2):
    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), thickness + 2)
    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness)

# ================== CORE ANALYSIS FUNCTION ==================
def analyze_face_landmarks(image, landmarks, width, height):
    def to_pixel(point_id):
        lm = landmarks.landmark[point_id]
        return int(lm.x * width), int(lm.y * height)

    chin = to_pixel(152)
    forehead = to_pixel(10)
    left_cheek = to_pixel(234)
    right_cheek = to_pixel(454)
    left_eye_outer = to_pixel(130)
    right_eye_outer = to_pixel(359)
    left_lip = to_pixel(61)
    right_lip = to_pixel(291)
    nose_tip = to_pixel(1)

    face_length = distance(forehead, chin) * 1.12
    face_width = distance(left_cheek, right_cheek)
    eye_width = distance(left_eye_outer, right_eye_outer)
    lip_width = distance(left_lip, right_lip)
    nose_to_lip = distance(
        nose_tip,
        ((left_lip[0] + right_lip[0]) // 2, (left_lip[1] + right_lip[1]) // 2)
    )

    ratio1 = round(face_length / face_width, 2)
    ratio2 = round(eye_width / face_width, 2)
    ratio3 = round(lip_width / nose_to_lip, 2)

    ideal_ratio = 1.618
    symmetry_score = round(100 - (abs(ideal_ratio - ratio1) / ideal_ratio * 100), 1)
    symmetry_score = max(0, min(100, symmetry_score))

    # Drawing
    outlined_text(image, "Golden Ratio Analyzer", (30, 40), (255, 255, 0), 0.8)
    outlined_text(image, f"Face Ratio: {ratio1}", (30, 80), (0, 255, 255))
    outlined_text(image, f"Eye Ratio:  {ratio2}", (30, 110), (255, 0, 255))
    outlined_text(image, f"Lip Ratio:  {ratio3}", (30, 140), (255, 255, 255))

    cv2.line(image, forehead, chin, (0, 255, 255), 2)
    cv2.line(image, left_cheek, right_cheek, (0, 255, 255), 2)
    cv2.line(image, left_eye_outer, right_eye_outer, (255, 0, 255), 2)
    cv2.line(image, left_lip, right_lip, (255, 255, 255), 2)

    return symmetry_score, ratio1, ratio2, ratio3

# ================== MAIN PROGRAM ==================
def main():
    global state, scan_start_time, final_score, final_ratios

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Webcam error")
        return

    print("SPACE: Start Scan | R: Reset | Q: Quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)

        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0]
            score, r1, r2, r3 = analyze_face_landmarks(frame, landmarks, w, h)

            # ================= STATE LOGIC =================
            if state == "IDLE":
                outlined_text(frame, "Press SPACE to start scan", (30, 200), (0, 255, 0))

            elif state == "SCANNING":
                elapsed = time.time() - scan_start_time
                scores_buffer.append(score)

                progress = min(elapsed / SCAN_DURATION, 1.0)
                bar_width = int(progress * 300)

                cv2.rectangle(frame, (30, 230), (30 + bar_width, 250), (0, 255, 0), -1)
                cv2.rectangle(frame, (30, 230), (330, 250), (255, 255, 255), 2)
                outlined_text(frame, f"Analyzing... {elapsed:.1f}s / {SCAN_DURATION}s",
                              (30, 220), (255, 255, 0))

                if elapsed >= SCAN_DURATION:
                    final_score = round(sum(scores_buffer) / len(scores_buffer), 1)
                    final_ratios = (r1, r2, r3)
                    state = "RESULT"

            elif state == "RESULT":
                outlined_text(frame, f"FINAL SCORE: {final_score}%",
                              (30, 220), (0, 255, 128), 1.0)
                outlined_text(frame, f"Face Ratio: {final_ratios[0]}", (30, 260), (255, 255, 255))
                outlined_text(frame, "Press R to reset", (30, 300), (200, 200, 200))

        else:
            outlined_text(frame, "No face detected", (30, 80), (0, 0, 255))

        outlined_text(frame, f"Mode: {mode}", (w - 220, 40), (255, 255, 255))

        cv2.imshow("Golden Ratio Analyzer", frame)
        key = cv2.waitKey(1) & 0xFF

        # ================= KEY CONTROLS =================
        if key == ord(' '):
            scores_buffer.clear()
            scan_start_time = time.time()
            state = "SCANNING"

        elif key == ord('r'):
            state = "IDLE"
            final_score = None
            final_ratios = None

        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()