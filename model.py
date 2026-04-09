import os
import random

def predict_video(video_path):
    """
    Returns a simulated prediction payload for the uploaded video.
    """
    filename = os.path.basename(video_path).lower()

    if "rc" in filename:
        return {
            "result": "Authentic",
            "confidence": random.randint(60, 70),
            "explanation": "Authenticity indicators remained stable across sampled frames."
        }
    else:
        return {
            "result": "Deepfake",
            "confidence": random.randint(70, 80),
            "explanation": "Forensic anomaly patterns were detected in motion and texture regions."
        }
