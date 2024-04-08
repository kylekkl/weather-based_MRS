import numpy as np
import pandas as pd
from flask import Flask, render_template, request
from pymongo import MongoClient
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from weather import Weather
from youtube import Youtube

# Constants and Global Variables
WEATHER_API = "38d2f4b13545a124018e68eab8c22a58"
YOUTUBE_API = "AIzaSyDTlzNah73XqK_uar2xatgJnh-uZa3jQK4"
MONGODB_URL = "mongodb+srv://kylekakili:kBdqAZk5IaYPiyPO@cluster0.b7zpfgx.mongodb.net/"

# AIzaSyDrte07cVXGrqHB_iawwowsU-Sv39JzHdE
# AIzaSyDzWCrerZ-eMXbuqhTldKNgsiyaDUAcEW4
# AIzaSyBlGzM3gF5929_bH4lCrG88sTn42kN4OrQ
USER_SESSION = {}
TEMP_SONG = {}
recommended = []
last_recommended_artist = None

# Flask App Initialization
app = Flask(__name__)

# Read the entire content
pd.set_option("display.max_colwidth", None)
# Dataset
df = pd.read_csv("updated_dataset.csv", encoding="latin1")


# Database Initialization
client = MongoClient(MONGODB_URL)
db = client.project_b
collection = db.weather_based_MRS

# TFIDF Vectorizer for Genre-Based Recommendations
df["genre_combined"] = df["genre"].apply(lambda x: " ".join(x.split(", ")))
tfidf_vectorizer = TfidfVectorizer()
tfidf_matrix = tfidf_vectorizer.fit_transform(df["genre_combined"])


# Route Definitions
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "city" in request.form:
            return handle_city_input()
        if "reaction" in request.form:
            return handle_reaction()
    return render_template(
        "index.html"
    )


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
        return render_template(
            "index.html",
            video_id=video_id,
            songs_listened=USER_SESSION.get("songs_listened", 0),
            amount_of_like=USER_SESSION.get("amount_of_like",0)
        )
    else:
        return render_template(
            "index.html", warning="Unable to determine mood from weather data."
        )


def handle_reaction():
    global USER_SESSION, SONG_LIST, TEMP_SONG, last_recommended_artist, recommended
    rating = request.form.get(
        "reaction", "Not Rated"
    )  # Set to default 'Not Rated' if reaction is not found, if user press like, rating = 'like'
    TEMP_SONG["rating"] = rating  # Adding key and values of rating
    update_user_session(TEMP_SONG)
    USER_SESSION["songs_listened"] = USER_SESSION.get("songs_listened", 0) + 1
    if TEMP_SONG["rating"] == "like":
        USER_SESSION["amount_of_like"] += 1
        collection.update_one(
            {"_id": USER_SESSION["_id"]},
            {"$set": {"amount_of_like": USER_SESSION["amount_of_like"]}},
        )  # Counting the amount of like

    if (
        USER_SESSION["amount_of_like"] >= 3
    ):  # At least liked 3 songs, then run the genre based
        data = collection.find_one({"_id": USER_SESSION["_id"]})
        liked_songs = [song for song in data["songs"] if song.get("rating") == "like"]
        liked_songs_df = pd.DataFrame(liked_songs)
        liked_songs_df["genre_combined"] = liked_songs_df["musicGenre"].apply(
            lambda x: " ".join(x.split(", "))
        )
        recommendations = generate_playlist_recos(df, liked_songs_df)
        if not recommendations.empty:
            for _, top_song in recommendations.iterrows():
                song_identifier = (top_song["name"], top_song["artist"])
                current_artist = top_song["artist"]
                if (
                    current_artist != last_recommended_artist
                    and song_identifier not in recommended
                ):
                    recommended.append(song_identifier)
                    last_recommended_artist = current_artist
                    song_name = top_song["name"]
                    artist_name = top_song["artist"]
                    TEMP_SONG = {
                        "nameOfSong": top_song["name"],
                        "artist": top_song["artist"],
                        "musicGenre": top_song["genre"],
                    }
                    search_query = f"{artist_name} - {song_name}"
                    yt = Youtube(api_key=YOUTUBE_API, search_query=search_query)
                    video_id = yt.get_result()
                    if video_id:
                        return render_template(
                            "index.html",
                            video_id=video_id,
                            songs_listened=USER_SESSION.get("songs_listened", 0),
                            amount_of_like=USER_SESSION.get("amount_of_like",0)
                        )
                    break
    return render_template(
        "index.html",
        video_id=get_song_video_id(),
        songs_listened=USER_SESSION.get("songs_listened", 0),
        amount_of_like=USER_SESSION.get("amount_of_like", 0),
    )


def get_song_video_id():
    global SONG_LIST, TEMP_SONG, last_recommended_artist, recommended
    if SONG_LIST is not None and not SONG_LIST.empty:
        while True:
            random_row = SONG_LIST.sample()  # Get a random row of the song list
            song_identifier = (
                random_row["name"].iloc[0],
                random_row["artist"].iloc[0],
            )  # Unique identifier for the song
            current_artist = random_row["artist"].iloc[0]
            # Check if the current artist is the same as the last recommended artist
            if (
                current_artist != last_recommended_artist
                and song_identifier not in recommended
            ):
                recommended.append(song_identifier)
                last_recommended_artist = (
                    current_artist  # Update the last recommended artist
                )

                TEMP_SONG = {
                    "nameOfSong": random_row["name"].to_string(index=False).strip(),
                    "artist": random_row["artist"].to_string(index=False).strip(),
                    "musicGenre": random_row["genre"].to_string(index=False).strip(),
                }
                search_query = f"{TEMP_SONG['artist']} - {TEMP_SONG['nameOfSong']}"
                yt = Youtube(api_key=YOUTUBE_API, search_query=search_query)
                return yt.get_result()


"""Update Database"""


def update_user_session(song_info):
    global USER_SESSION
    collection.update_one({"_id": USER_SESSION["_id"]}, {"$push": {"songs": song_info}})


def create_feature_set(df):
    tfidf = TfidfVectorizer()
    tfidf_matrix = tfidf.fit_transform(df["genre_combined"])
    genre_df = pd.DataFrame(tfidf_matrix.toarray())
    genre_df.columns = ["genre" + "|" + i for i in tfidf.get_feature_names_out()]

    return genre_df


def generate_playlist_recos(df, user_df):
    df_features = create_feature_set(df)
    user_features = create_feature_set(user_df)

    # Ensure both feature sets have the same columns
    common_columns = df_features.columns.intersection(user_features.columns)
    df_features = df_features[common_columns]
    user_features = user_features[common_columns]

    # Calculate similarity
    df["sim"] = cosine_similarity(
        df_features, user_features.mean().values.reshape(1, -1)
    )[:, 0]
    top_recommendation = df.sort_values("sim", ascending=False).head(5)

    return top_recommendation


if __name__ == "__main__":
    app.run(debug=True)
