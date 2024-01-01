import googleapiclient.discovery


class Youtube:
    def __init__(self, api_key, search_query):
        self.api_key = api_key
        self.search_query = search_query
        self.youtube = googleapiclient.discovery.build(
            "youtube", "v3", developerKey=self.api_key
        )
    
    def get_result(self):
        try:
            result = (
                self.youtube.search()
                .list(q=self.search_query, type="video", part="id", maxResults=1)
                .execute()
            )
            items = result.get("items", [])
            if not items:
                return None  # No results found
            return items[0]["id"]["videoId"]
        except Exception as e:
            print("Error fetching video from YouTube:", e)
            return None