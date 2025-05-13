import firebase_admin
from firebase_admin import credentials, firestore
import matplotlib.pyplot as plt
from util import clean_timestamp
import numpy as np
from datetime import datetime
from collections import defaultdict
import math
from matplotlib.lines import Line2D
import pandas as pd
import seaborn as sns
from util import display_menu

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

    support_line = Line2D([0], [0], color='red', linestyle='--', label='Support (NPC Help)')
    fig.legend(handles=[support_line], loc='upper left', ncol=1, fontsize=10)
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

def plot_player_feedback(events):
    """
        Plot a stacked bar chart that shows how players respond to NPC's suggestions
    """
    choice_count = defaultdict(int)
    for event in events:
        if event.get("eventType") == "player_response":
            if event.get('playerChoice') == 'skip':
                choice_count['Rejected'] += 1
            else:
                choice_count['Accepted'] += 1
        
    labels = list(choice_count.keys())
    counts = list(choice_count.values())

    _, ax = plt.subplots()
    ax.bar("Category", counts[0], label=labels[0], color='red')
    ax.bar("Category", counts[1], label=labels[1], color='green')
    ax.set_ylabel("Count")
    ax.set_title("Grace's Suggestion: Accepted or Rejected")
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=2)
    plt.tight_layout()
    plt.show()

def plot_emotion_flow(events, interval=1):
    """
        Plot a heatmap that visually demonstrates how emotions change over time

        interval: interval in minutes between emotion buckets
    """
    emotion_times = defaultdict(lambda: defaultdict(int))
    events.sort(key=lambda event: datetime.fromisoformat(event['timestamp'].replace("Z", "+00:00")))
    base_time = None

    for event in events:
        if event.get('eventType') != "emotion_log":
            continue
    
        ts = datetime.fromisoformat(event['timestamp'].replace("Z", "+00:00"))
        if not base_time:
            base_time = ts

        minutes = int((ts - base_time).total_seconds() / 60)
        bucket = (minutes // interval) * interval

        emotion = event.get("emotion")
        if emotion:
            emotion_times[bucket][emotion] += 1

    # Convert to DataFrame
    df = pd.DataFrame(emotion_times).fillna(0).T.sort_index()

    plt.figure(figsize=(12, 6))
    sns.heatmap(df.T, cmap='YlGnBu', annot=True, fmt='g')
    plt.xlabel("Time (minutes)")
    plt.ylabel("Emotion")
    plt.title("Emotion-State Heatmap Over Time")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    db = connect_firebase(FS_CERTIFICATE)
    docs = extract_queries_from_collection('sessions_web', db)
    all_events = extract_events('sessions_web', db, docs)

    exit = False
    while not exit:
        display_menu()
        choice = int(input("Your Choice(1-5): ").strip())
        if choice == 1:
            docs = extract_queries_from_collection('sessions_web', db)
            durations = extract_duration(docs)
            plot_duration(durations)
        elif choice == 2:
            plot_emotion_trend_with_markers(all_events)
        elif choice == 3:
            plot_player_feedback(all_events)
        elif choice == 4:
            plot_emotion_flow(all_events)
        elif choice == 5:
            exit = True
        else:
            print("Invalid input. Please enter again.")
    
    