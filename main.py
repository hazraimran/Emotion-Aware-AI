import firebase_admin
from firebase_admin import credentials, firestore
import matplotlib.pyplot as plt
from util import clean_timestamp
import numpy as np
from datetime import datetime
from collections import defaultdict
import math

# Path to google firebase service account certificate
FS_CERTIFICATE = './firebase-admin.json'

def connect_firebase(cred_path):
    """
        Authenticate with Google Firestore database and returns a connection client.

        cred: path to firebase service account certificate

        Return: firestore database client object
    """
    # Verify certificate and initialize app
    creds = credentials.Certificate(FS_CERTIFICATE)
    firebase_admin.initialize_app(creds)

    # Connect to Firestore
    db = firestore.client()

    return db

def extract_queries_from_collection(collection:str, db):
    """
        Fetch all query objects from a firestore collection
    
        collection: name of firestore collection
        db: firestore database client 

        Return: a list of QuerySnapshot objects
    """
    session = db.collection(collection)
    queries = session.stream()

    return queries

def extract_duration(queries):
    """
        Pull duration data of each session from Firestore database.

        queries: a list of firestore QuerySnapshot object

        Return: a list of integer durations 
    """
    durations = []
    for query in queries:
        doc_dict = query.to_dict()
        start = doc_dict.get("sessionStartTime")
        end = doc_dict.get("sessionEndTime")

        if start and end:
            try:
                start_dt = clean_timestamp(start)
                end_dt = clean_timestamp(end)
                duration = (end_dt - start_dt).total_seconds() / 60 
                durations.append(round(duration, 0))
            except Exception as e:
                print(f"Skipping collection instance due to error {e}")

    return durations

def extract_events(collection:str, db, queries:list, subcollection:str = 'events'):
    """
        Pulls nested subcollection from a given collection.
        
        collection: name of firestore collection
        queries: a list of query objects in collection
        db: firestore database client object
        subcollection: nested subcollection within collection. Default to 'events'

        Return: a list of dictionary containing data of items from subcollection
    """
    all_events = []
    for query in queries:
        # Retrive documents in collection by ID
        ref = db.collection(collection).document(query.id)
        # Get all events in document
        events = ref.collection(subcollection).stream()
        for event in events:
            all_events.append(event.to_dict())

    return all_events

def plot_emotion_trend_with_markers(events):
    """
        Plots a line chart illustrating change of emotions over time.

        events: a list of dictionary containing event fields
    """
    # Separate emotion logs and support events
    emotion_logs = []
    support_times = []

    for event in events:
        ts = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
        
        if event.get("eventType") == "emotion_log":
            emotion_logs.append((ts, event))
        elif event.get("eventType") == "npc_response" and event.get("npcAction") == "helpmode":
            support_times.append(ts)

    # Sort emotion logs chronologically
    emotion_logs.sort(key=lambda x: x[0])

    # Build emotion time series
    emotion_series = defaultdict(list)
    emotion_times = []

    for idx, (ts, entry) in enumerate(emotion_logs):
        emotion_times.append(ts)
        for emotion, value in entry.get("probabilities", {}).items():
            emotion_series[emotion].append((idx, value))

    # Create subplots
    emotions = sorted(emotion_series.keys())
    cols = 3
    rows = math.ceil(len(emotions) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 5, rows * 3), sharex=True)
    axes = axes.flatten()

    # Plot emotion trends over time step
    emotion_to_ax = {}
    for i, emotion in enumerate(emotions):
        ax = axes[i]
        series = emotion_series[emotion]
        if series:
            x, y = zip(*series)
            ax.plot(x, y, label=emotion)
            ax.set_title(emotion.capitalize())
            ax.set_ylim(0, 1)
            ax.grid(True)
            emotion_to_ax[emotion] = ax
        else:
            ax.set_visible(False)
    
    # Plot support markers only on dominant emotion subplot
    for st in support_times:
        # Find closest emotion log time step
        closest_idx = min(
            range(len(emotion_times)),
            key=lambda i: abs((emotion_times[i] - st).total_seconds())
        )
        _, closest_log = emotion_logs[closest_idx]

        # Determine dominant emotion
        probs = closest_log.get("probabilities", {})
        if probs:
            dominant_emotion = max(probs, key=probs.get)
            ax = emotion_to_ax.get(dominant_emotion)
            if ax:
                ax.axvline(x=closest_idx, color='red', linestyle='--', alpha=0.6)

    # Turn off unused axes
    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)

    fig.supxlabel("Time Step")
    fig.supylabel("Probability")
    plt.suptitle("Emotion Trends Over Time with Support Markers", fontsize=16)
    plt.tight_layout()
    plt.show()

    
def plot_duration(durations:list):
    """
        Plot a histogram that shows distribution of session duration.

        durations: a list of session durations
    """
    min_duration = min(durations)
    max_duration = max(durations)
    bins = np.arange(min_duration, max_duration+2, step=1)

    # Create histogram
    plt.figure(figsize=(10, 6))
    plt.hist(durations, bins=bins, color='skyblue', edgecolor='black')
    plt.title("Distribution of Session Durations")
    plt.xlabel("Duration in Minutes (right end exclusive)")
    plt.ylabel("Number of Sessions")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    db = connect_firebase(FS_CERTIFICATE)
    docs = extract_queries_from_collection('sessions_web', db)
    all_events = extract_events('sessions_web', db, docs)
    plot_emotion_trend_with_markers(all_events)