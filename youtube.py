import googleapiclient.discovery


class Youtube:
    def __init__(self, api_key, search_query):
        self.api_key = api_key
        self.search_query = search_query
        self.youtube = googleapiclient.discovery.build(
            "youtube", "v3", developerKey=self.api_key
        )
    
    def get_result(self):
        result = (
            self.youtube.search()
            .list(q=self.search_query, type="video", part="id", maxResults=1)
            .execute()
        )
        return result.get("items", [])[0]["id"]["videoId"]

