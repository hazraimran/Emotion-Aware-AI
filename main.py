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
    print(all_events[0])