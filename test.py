import pandas as pd
import numpy as np
from flask import Flask, render_template, request
from pymongo import MongoClient
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from youtube import Youtube

# Constants and Global Variables
YOUTUBE_API = "AIzaSyDzWCrerZ-eMXbuqhTldKNgsiyaDUAcEW4"
MONGODB_URL = "mongodb+srv://kylekakili:kBdqAZk5IaYPiyPO@cluster0.b7zpfgx.mongodb.net/"

USER_SESSION = {
    "songs": [],
    "amount_of_like": 0,
}
TEMP_SONG = {}
recommended = []
# Flask App Initialization
app = Flask(__name__)
pd.set_option("display.max_colwidth", None)
# Dataset for Genre-Based Recommendations
genre_based_df = pd.read_csv("./dataset/data_with_genres.csv")

# Database Initialization
client = MongoClient(MONGODB_URL)
db = client.project_a
collection = db.content_based_MRS

# TFIDF Vectorizer for Genre-Based Recommendations
genre_based_df["genre_combined"] = genre_based_df["genre"].apply(lambda x: " ".join(x.split(", ")))
tfidf_vectorizer = TfidfVectorizer()
tfidf_matrix = tfidf_vectorizer.fit_transform(genre_based_df["genre_combined"])

# Additional Functions for Song Recommendations
def create_feature_set(df):
    # Ensure 'genre_combined' column is present
    if 'genre_combined' not in df.columns:
        df["genre_combined"] = "default"  # Default value if genre information is missing

    tfidf = TfidfVectorizer()
    tfidf_matrix = tfidf.fit_transform(df['genre_combined'])
    genre_df = pd.DataFrame(tfidf_matrix.toarray())
    genre_df.columns = ['genre' + "|" + i for i in tfidf.get_feature_names_out()]

    return genre_df

def generate_playlist_recos(df, playlist_df):
    df_features = create_feature_set(df)
    playlist_features = create_feature_set(playlist_df)

    # Ensure both feature sets have the same columns
    common_columns = df_features.columns.intersection(playlist_features.columns)
    df_features = df_features[common_columns]
    playlist_features = playlist_features[common_columns]

    # Calculate similarity
    df['sim'] = cosine_similarity(df_features, playlist_features.mean().values.reshape(1, -1))[:, 0]
    top_recommendation = df.sort_values('sim', ascending=False).head(1)

    return top_recommendation

# Route Definitions
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        collection.insert_one(USER_SESSION)
        video_id = get_song_video_id()
        return render_template("index.html", video_id=video_id)
    elif request.method == "POST":
        if "reaction" in request.form:
            return handle_reaction()
    return render_template("index.html", video_id=get_song_video_id())

def handle_reaction():
    global USER_SESSION, genre_based_df, recommended
    rating = request.form.get("reaction", "Not Rated")
    TEMP_SONG["rating"] = rating
    update_user_session(TEMP_SONG)

    if TEMP_SONG["rating"] == "like":
        USER_SESSION["amount_of_like"] += 1
        collection.update_one(
            {"_id": USER_SESSION["_id"]},
            {"$set": {"amount_of_like": USER_SESSION["amount_of_like"]}}
        )

    if USER_SESSION["amount_of_like"] >= 3:
        data = collection.find_one({"_id": USER_SESSION["_id"]})
        user_preferences = {}
        user_preferences['genre'] = [song['musicGenre'] for song in data['songs']]
        liked_songs = [song for song in data['songs'] if song.get('rating') == 'like']
        liked_songs_df = pd.DataFrame(liked_songs)        
        liked_songs_df["genre_combined"] = liked_songs_df["musicGenre"].apply(lambda x: " ".join(x.split(", ")))
        recommendations = generate_playlist_recos(genre_based_df, liked_songs_df)
        
        if not recommendations.empty:
            top_song = recommendations.iloc[0]
            song_name = top_song['name']
            artist_name = top_song['artist']
            search_query = f"{artist_name} - {song_name}"
            yt = Youtube(api_key=YOUTUBE_API, search_query=search_query)
            video_id = yt.get_result()
            if video_id:
                return render_template("index.html", video_id=video_id)

    return render_template("index.html", video_id=get_song_video_id())


def get_song_video_id():
    global genre_based_df, TEMP_SONG, recommended
    while True:
        random_row = genre_based_df.sample()
        song_identifier = (random_row["name"].iloc[0], random_row["artist"].iloc[0])

        # Check if the song is already in the recommended list
        if song_identifier not in recommended:
            recommended.append(song_identifier)
            TEMP_SONG = {
                "nameOfSong": random_row["name"].to_string(index=False).strip(),
                "artist": random_row["artist"].to_string(index=False).strip(),
                "musicGenre": random_row["genre"].to_string(index=False).strip(),
            }
            search_query = f"{TEMP_SONG['artist']} - {TEMP_SONG['nameOfSong']}"
            yt = Youtube(api_key=YOUTUBE_API, search_query=search_query)
            return yt.get_result()

        if len(recommended) >= len(genre_based_df):
            return None

def update_user_session(song_info):
    global USER_SESSION
    collection.update_one({"_id": USER_SESSION["_id"]}, {"$push": {"songs": song_info}})

if __name__ == "__main__":
    app.run(debug=True)
