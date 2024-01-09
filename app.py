import numpy as np
import pandas as pd
from flask import Flask, render_template, request
from pymongo import MongoClient
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from weather import Weather
from youtube import Youtube

# Constants and Global Variables
WEATHER_API = "adea9ed55a37f7a427463f3cde699948"
YOUTUBE_API = "AIzaSyDzWCrerZ-eMXbuqhTldKNgsiyaDUAcEW4"
#AIzaSyDrte07cVXGrqHB_iawwowsU-Sv39JzHdE
#AIzaSyDzWCrerZ-eMXbuqhTldKNgsiyaDUAcEW4
#AIzaSyBlGzM3gF5929_bH4lCrG88sTn42kN4OrQ
MONGODB_URL = "mongodb+srv://kylekakili:kBdqAZk5IaYPiyPO@cluster0.b7zpfgx.mongodb.net/"
USER_SESSION = {
    "location": "",
    "mood": "",
    "songs": [],
    "amount_of_like": 0,
    "recommended_songs": set(),
    
}
TEMP_SONG = {}


# Flask App Initialization
app = Flask(__name__)

# Read the entire content
pd.set_option("display.max_colwidth", None)
# Dataset for Weather-Based Recommendations
df = pd.read_csv("./dataset/music_dataset_with_genres.csv")

# Dataset for Genre-Based Recommendations
genre_based_df = pd.read_csv("./dataset/data_with_genres.csv")

# Database Initialization
client = MongoClient(MONGODB_URL)
db = client.project_a
collection = db.music_recommendation_system

# TFIDF Vectorizer for Genre-Based Recommendations
genre_based_df["genre_combined"] = genre_based_df["genre"].apply(
    lambda x: " ".join(x.split(", "))
)
tfidf_vectorizer = TfidfVectorizer()
tfidf_matrix = tfidf_vectorizer.fit_transform(genre_based_df["genre_combined"])


# Route Definitions
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "city" in request.form:
            return handle_city_input()
        if "reaction" in request.form:
            return handle_reaction()
    return render_template("index.html")


def handle_city_input():
    global USER_SESSION, SONG_LIST
    location = request.form.get("city", "").title()  # Get location from user
    if not location:
        return render_template("index.html", warning="Please enter your current city.")

    weather = Weather(api_key=WEATHER_API, city=location)
    (
        temperature,
        weather_condition,
    ) = weather.get_weather()  # Get temperature and condition from weather class
    mood = weather.get_mood(
        temperature, weather_condition
    )  # Get the corresponding mood
    USER_SESSION = {
        "location": location,
        "mood": mood,
        "songs": [],
        "amount_of_like": 0,
    }
    collection.insert_one(USER_SESSION)

    if mood:
        SONG_LIST = df[
            df["mood"] == mood
        ]  # Save the song if the mood column is equal to the mood that presented
        video_id = get_song_video_id()
        return render_template("index.html", video_id=video_id)
    else:
        return render_template(
            "index.html", warning="Unable to determine mood from weather data."
        )


def handle_reaction():
    global USER_SESSION, SONG_LIST
    rating = request.form.get(
        "reaction", "Not Rated"
    )  # Set to default 'Not Rated' if reaction is not found, if user press like, rating = 'like'
    TEMP_SONG["rating"] = rating  # Adding key and values of rating
    update_user_session(TEMP_SONG)
    if TEMP_SONG["rating"] == "like":
        USER_SESSION["amount_of_like"] += 1
        collection.update_one(
            {"_id": USER_SESSION["_id"]},
            {"$set": {"amount_of_like": USER_SESSION["amount_of_like"]}},
        )  # Counting the amount of like

    if (
        USER_SESSION["amount_of_like"] >= 3
    ):  # At least liked 3 songs, then run the genre based
        return recommend_based_on_genre()
    else:
        if SONG_LIST is not None and not SONG_LIST.empty:
            video_id = (
                get_song_video_id()
            )  # Else keep using the first dataset with the mood
            return render_template("index.html", video_id=video_id)
    return render_template("index.html")


recommended = []


last_recommended_artist = None

def get_song_video_id():
    global SONG_LIST, TEMP_SONG, last_recommended_artist
    if SONG_LIST is not None and not SONG_LIST.empty:
        while True:
            random_row = SONG_LIST.sample()  # Get a random row of the song list
            song_identifier = (
                random_row["name"].iloc[0],
                random_row["artist"].iloc[0],
            )  # Unique identifier for the song

            current_artist = random_row["artist"].iloc[0]

            # Check if the current artist is the same as the last recommended artist
            if current_artist != last_recommended_artist and song_identifier not in recommended:
                recommended.append(song_identifier)
                last_recommended_artist = current_artist  # Update the last recommended artist

                TEMP_SONG = {
                    "nameOfSong": random_row["name"].to_string(index=False),
                    "artist": current_artist,
                    "musicGenre": random_row["genre"].to_string(index=False),
                }
                search_query = f"{TEMP_SONG['artist']} - {TEMP_SONG['nameOfSong']}"
                yt = Youtube(api_key=YOUTUBE_API, search_query=search_query)
                return yt.get_result()

            if len(recommended) >= len(SONG_LIST):
                # All songs have been recommended, handle this case
                return None



"""Update Database"""


def update_user_session(song_info):
    global USER_SESSION
    collection.update_one({"_id": USER_SESSION["_id"]}, {"$push": {"songs": song_info}})


def recommend_based_on_genre():
    global USER_SESSION, SONG_LIST, tfidf_vectorizer, tfidf_matrix, genre_based_df
    user_preferences = collection.find_one({"_id": USER_SESSION["_id"]})

    liked_genres = set()
    for song in user_preferences["songs"]:
        if song["rating"] == "like":
            genres = song["musicGenre"].split(", ")
            liked_genres.update(genres)

    user_genres_combined = " ".join(liked_genres)
    user_tfidf_vector = tfidf_vectorizer.transform([user_genres_combined])
    cosine_similarities = cosine_similarity(user_tfidf_vector, tfidf_matrix)

    sorted_indices = np.argsort(cosine_similarities[0])[::-1]
    previously_recommended_songs = {
        song["nameOfSong"] for song in user_preferences["songs"]
    }

    for idx in sorted_indices:
        recommended_song = genre_based_df.iloc[idx]
        if recommended_song["name"] not in previously_recommended_songs:
            SONG_LIST = recommended_song.to_frame().T
            video_id = get_song_video_id()
            if video_id is not None:
                return render_template("index.html", video_id=video_id)

    # If no new songs are found
    return render_template(
        "index.html", warning="No new songs found based on your preferences."
    )



if __name__ == "__main__":
    app.run(debug=True)
