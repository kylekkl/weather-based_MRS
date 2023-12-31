from weather import Weather
from youtube import Youtube
import pandas as pd

WEATHER_API = "adea9ed55a37f7a427463f3cde699948"
YOUTUBE_API = "AIzaSyDrte07cVXGrqHB_iawwowsU-Sv39JzHdE"

location = input("Enter you city: ").title()
weather = Weather(api_key=WEATHER_API, city=location)
temperature, weather_condition = weather.get_weather()
mood = weather.get_mood(temperature, weather_condition)

print(f"Temperature in {location}: {temperature}°C")
print(f"Weather Condition: {weather_condition}")
print(f"Mood: {mood}")

df = pd.read_csv(".\dataset\music_dataset.csv")

song_list = df[df["mood"] == mood]
random_row = song_list.sample()
artist = random_row["artist"].to_string(index=False)
song = random_row["name"].to_string(index=False)
music_genre = random_row["Genre"].to_string(index=False)
search_item = f"{artist} - {song}"

yt = Youtube(api_key=YOUTUBE_API, search_query=search_item)
print(search_item)
yt.link_to_video()


