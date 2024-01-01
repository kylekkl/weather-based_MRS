import requests
WEATHER_CONDITIONS = {
    "Thunderstorm": [
        "thunderstorm with light rain",
        "thunderstorm with rain",
        "thunderstorm with heavy rain",
        "light thunderstorm",
        "thunderstorm",
        "heavy thunderstorm",
        "ragged thunderstorm",
        "thunderstorm with light drizzle",
        "thunderstorm with drizzle",
        "thunderstorm with heavy drizzle",
    ],
    "Drizzle": [
        "light intensity drizzle",
        "drizzle",
        "heavy intensity drizzle",
        "light intensity drizzle rain",
        "drizzle rain",
        "heavy intensity drizzle rain",
        "shower rain and drizzle",
        "heavy shower rain and drizzle",
        "shower drizzle",
    ],
    "Rain": [
        "light rain",
        "moderate rain",
        "heavy intensity rain",
        "very heavy rain",
        "extreme rain",
        "freezing rain",
        "light intensity shower rain",
        "shower rain",
        "heavy intensity shower rain",
        "ragged shower rain",
    ],
    "Snow": [
        "light snow",
        "snow",
        "heavy snow",
        "sleet",
        "light shower sleet",
        "shower sleet",
        "light rain and snow",
        "rain and snow",
        "light shower snow",
        "shower snow",
        "heavy shower snow",
    ],
    "Mist": ["mist"],
    "Clear": ["clear sky"],
    "Clouds": ["few clouds", "scattered clouds", "broken clouds", "overcast clouds"],
}
URL = "http://api.openweathermap.org/data/2.5/weather"
class Weather:
    def __init__(self,api_key,city):
        self.api_key = api_key
        self.city = city
    
    #* get the data from OpenWeather
    def get_weather(self):
        params = {
        "q": self.city,
        "appid": self.api_key,
        "units": "metric",  #* To get temperature in Celsius
        }
        response = requests.get(URL, params=params)
        if response.status_code == 200:
            data = response.json()
            temperature = data["main"]["temp"]
            weather_condition = data["weather"][0]["description"]
            return temperature, weather_condition
        else:
            return None, None 
    
    #*Determine mood by temperature and weather condition
    def get_mood(self,temperature, weather_condition):
        if temperature is None or weather_condition is None:
            print("Error: Weather data is incomplete.")
            return None
        if (
        weather_condition in WEATHER_CONDITIONS["Clear"]
        or weather_condition in WEATHER_CONDITIONS["Clouds"]
    ) and (temperature >= 21 and temperature <= 32):
            return "Happy"
        elif weather_condition in WEATHER_CONDITIONS["Clouds"] and temperature < 21:
            return "Calm"
        elif weather_condition in WEATHER_CONDITIONS["Clear"] and temperature < 21:
            return "Energetic"
        elif (
            weather_condition in WEATHER_CONDITIONS["Rain"]
            or weather_condition in WEATHER_CONDITIONS["Thunderstorm"]
            or weather_condition in WEATHER_CONDITIONS["Snow"]
            or temperature > 32
        ):
            return "Sad"
        elif (
            weather_condition in WEATHER_CONDITIONS["Drizzle"]
            or weather_condition in WEATHER_CONDITIONS["Mist"]
            or temperature < 21
        ):
            return "Calm"
        else:
            print("Error: Weather data is incomplete.")
            return None
        