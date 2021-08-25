import requests
import json
from datetime import datetime

class TwitterClient:
    def __init__(self):
        with open("config.json") as f:
            config = json.load(f)
            self.token = "Bearer " + config["BEARER"]
            self.last_tweet_id = None

    def search_tweets(self, min_retweets = 1000, min_faves = 1000):
        endpoint = "https://api.twitter.com/2/tweets/search/recent"
        headers = {
            "Authorization": self.token
        }
        if self.last_tweet_id is not None:
            time_interval = "since_id:{}".format(self.last_tweet_id)
        else:
            time_interval = "since:{}".format(datetime.today().strftime("%Y-%m-%d"))
        params = {
            "q": "(crypto OR cryptocurrency OR defi OR nft) lang:en -giveaway -giveaways -rt -retweet -retweets -follower -followers min_retweets:{} min_faves:{} {}".format(min_retweets, min_faves, time_interval),
            "tweet_mode": "extended",
            "result_type": "popular",
            "count": 2,
        }
        res = requests.get(endpoint, headers = headers, params = params)
        res = res.json()
        for tweet_obj in res["statuses"]:
            self.last_tweet_id = tweet_obj["id"] if self.last_tweet_id is None else max(self.last_tweet_id, tweet_obj["id"])
            print("Likes:{} Retweets:{} Content:\"{}\"".format(tweet_obj["favorite_count"], tweet_obj["retweet_count"], tweet_obj["full_text"]))


def check_API_usage():
    endpoint = "https://api.twitter.com/1.1/application/rate_limit_status.json"
    headers = {
        "Authorization": "Bearer " + token
    }
    res = requests.get(endpoint, headers = headers)
    print(res.json())


client = TwitterClient()
client.search_tweets()
