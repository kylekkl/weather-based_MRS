import pandas as pd
from flask import Flask, render_template, request
from pymongo import MongoClient

from weather import Weather
from youtube import Youtube

# Constants and Global Variables
WEATHER_API = "adea9ed55a37f7a427463f3cde699948"
YOUTUBE_API = "AIzaSyDrte07cVXGrqHB_iawwowsU-Sv39JzHdE"
SONG_LIST = None
MONGODB_URL = "mongodb+srv://kylekakili:kBdqAZk5IaYPiyPO@cluster0.b7zpfgx.mongodb.net/"
USER_SESSION = {}
TEMP_SONG = {}
# Flask App Initialization
app = Flask(__name__)

# Dataset
df = pd.read_csv("./dataset/music_dataset.csv")

# Database
client = MongoClient(MONGODB_URL)
db = client.project_a
collection = db.music_recommendation_system


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
    global SONG_LIST, USER_SESSION
    location = request.form.get("city", None).title()
    if not location:
        return render_template("index.html", warning="Please enter your current city.")
    weather = Weather(api_key=WEATHER_API, city=location)
    temperature, weather_condition = weather.get_weather()
    mood = weather.get_mood(temperature, weather_condition)
    USER_SESSION = {"location": location, "mood": mood, "songs": []}
    # insert_result = collection.insert_one(USER_SESSION)
    # USER_SESSION["_id"] = insert_result.inserted_id
    if mood is None:
        return render_template(
            "index.html", warning="Unable to determine mood from weather data."
        )
    SONG_LIST = df[df["mood"] == mood]
    # If SONG_LIST is not empty, get the first song and its video ID
    if not SONG_LIST.empty:
        video_id = get_song_video_id()
        return render_template("index.html", video_id=video_id)
    else:
        # If no songs are found for the mood, show a message
        return render_template(
            "index.html", warning="No songs found for your current mood."
        )


def handle_reaction():
    global SONG_LIST, TEMP_SONG
    rating = "Not Rated"
    if "reaction" in request.form:
        rating = request.form.get("reaction")
        TEMP_SONG["rating"] = rating
        # update_user_session(TEMP_SONG)
    if SONG_LIST is not None and not SONG_LIST.empty:
        video_id = get_song_video_id()
        return render_template("index.html", video_id=video_id)


def get_song_video_id():
    global SONG_LIST, USER_SESSION, TEMP_SONG

    if SONG_LIST is not None and not SONG_LIST.empty:
        random_row = SONG_LIST.sample()
        artist = random_row["artist"].to_string(index=False)
        song = random_row["name"].to_string(index=False)
        music_genre = random_row["Genre"].to_string(index=False)
        search_item = f"{artist} - {song}"
        TEMP_SONG = {
            "nameOfSong": song,
            "artist": artist,
            "musicGenre": music_genre,
        }
        yt = Youtube(api_key=YOUTUBE_API, search_query=search_item)
        video_id = yt.get_result()
        SONG_LIST = SONG_LIST.drop(random_row.index)
        return video_id
    return None


def update_user_session(TEMP_SONG):
    global USER_SESSION
    try:
        collection.update_one(
            {"_id": USER_SESSION["_id"]}, {"$push": {"songs": TEMP_SONG}}
        )
    except Exception as e:
        print("Error updating the Database:", e)


# Uncomment and complete this method to handle database saving
# def save_user_reaction(location, rating, video_id):
#     data = {
#         "location": location,
#         "rating": rating,
#         "video_id": video_id
#     }
#     try:
#         collection.insert_one(data)
#     except Exception as e:
#         print("Error saving to Database:", e)

# Main Execution
if __name__ == "__main__":
    app.run(debug=True)
