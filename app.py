import pandas as pd
from flask import Flask, redirect, render_template, request, url_for
from pymongo import MongoClient

from weather import Weather
from youtube import Youtube

WEATHER_API = "adea9ed55a37f7a427463f3cde699948"
YOUTUBE_API = "AIzaSyDrte07cVXGrqHB_iawwowsU-Sv39JzHdE"
df = pd.read_csv(
    ".\dataset\music_dataset.csv"
)
app = Flask(__name__)
try:
    client = MongoClient("localhost", 27017)
    db = client.MRS_database
    WMRS = db.WMRS
except Exception as e:
    print("Error connecting to Database:", e)


@app.route("/", methods=["GET", "POST"])
def index():
    video_id = None
    warning = None
    if request.method == "POST":
        location = request.form["city"].title()
        if not location:
            warning = "Please enter your current city."
        else:
            weather = Weather(api_key=WEATHER_API, city=location)
            temperature, weather_condition = weather.get_weather()
            mood = weather.get_mood(temperature, weather_condition)
            song_list = df[df["mood"] == mood]
            random_row = song_list.sample()
            artist = random_row["artist"].to_string(index=False)
            song = random_row["name"].to_string(index=False)
            # music_genre = random_row["Genre"].to_string(index=False)
            search_item = f"{artist} - {song}"
            yt = Youtube(api_key=YOUTUBE_API, search_query=search_item)
            video_id = yt.get_result()
            if mood is None:
                pass
    return render_template("index.html", video_id=video_id, warning=warning)


if __name__ == "__main__":
    app.run()
