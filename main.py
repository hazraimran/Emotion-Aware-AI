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

def plot_emotion_trend(events):
    """
        Plots a line chart illustrating change of emotions over time.

        events: a list of dictionary containing event fields
    """
    # Get all emotion logs
    emotion_logs = [
        e for e in events if e.get('eventType') == 'emotion_log'
    ]

    # Sort by timestamp
    emotion_logs.sort(key=lambda x: datetime.fromisoformat(x['timestamp'].replace("Z", "+00:00")))

    # Collection probability of different emotions over event index
    emotion_series = defaultdict(list)
    for idx, entry in enumerate(emotion_logs):
        probs = entry.get('probabilities')
        for emotion, val in probs.items():
            emotion_series[emotion].append((idx, val))

    # Create subplots
    emotions = sorted(emotion_series)
    num_emotions = len(emotions)
    cols = 3
    rows = math.ceil(num_emotions / cols)

    fig, axes = plt.subplots(rows, cols, figsize=(cols * 5, rows * 3), sharex=True)
    axes = axes.flatten()

    for i, emotion in enumerate(emotions):
        ax = axes[i]
        series = emotion_series[emotion]
        if series:
            x, y = zip(*series)
            ax.plot(x, y, label=emotion)
            ax.set_title(emotion.capitalize())
            ax.set_ylim(0, 1)
            ax.grid(True)
        else:
            ax.set_visible(False)
    
    plt.suptitle("Emotion Trends Over Time (One Subplot per Emotion)", fontsize=16)
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
    plot_emotion_trend(all_events)