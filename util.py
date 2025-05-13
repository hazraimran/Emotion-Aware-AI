"""
    A set of utility functions for supporting data analytics 
"""

from datetime import datetime
import re

def clean_timestamp(ts_str):
    """
        Clean firestore generated timestamp and convert it to datetime object
    """

    # Replace Z with +00:00 for timezone compatibility
    ts_str = ts_str.replace("Z", "+00:00")

    # Regex to truncate fractional seconds to 6 digits
    ts_str = re.sub(r'\.(\d{6})\d+', r'.\1', ts_str)

    return datetime.fromisoformat(ts_str)

def display_menu():
    """
        Display program menus to users
    """
    print("=================Grace's Performance====================")
    print("1) Plot Duration\n2) Plot Emotion Trends\n3) Plot Player Feedback\n4) Plot Emotion Flow(Heatmap)\n5) Exit\n")