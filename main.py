import firebase_admin
from firebase_admin import credentials, firestore
import matplotlib.pyplot as plt
from util import clean_timestamp
import numpy as np

# Path to google firebase service account certificate
FS_CERTIFICATE = './firebase-admin.json'

def connect_firebase(cred_path):
    """
        Authenticate with Google Firestore database and returns a connection client.

        cred: path to firebase service account certificate
    """
    # Verify certificate and initialize app
    creds = credentials.Certificate(FS_CERTIFICATE)
    firebase_admin.initialize_app(creds)

    # Connect to Firestore
    db = firestore.client()

    return db

def extract_duration(collection_name, db):
    """
        Pull duration data of each session from Firestore database.

        collection_name: firestore collection name
        db: firestore database client 

        Return: a list of durations
    """
    # Pull data collection from firestore
    session = db.collection(collection_name)

    # Stream data from collection
    docs = session.stream()

    durations = []
    for doc in docs:
        doc_dict = doc.to_dict()
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

def plot_duration(durations:list):
    """
        Plot a histogram that shows distribution of session duration

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

db = connect_firebase(FS_CERTIFICATE)
durations = extract_duration("sessions_web", db)
plot_duration(durations)