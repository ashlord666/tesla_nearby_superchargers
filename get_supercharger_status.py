from rauth import OAuth2Service
import json
import sys
import logging
import time
import traceback
from datetime import datetime
from twython import Twython
from tendo import singleton
from logging.handlers import TimedRotatingFileHandler

# region init
me = singleton.SingleInstance()
# create logger
logger = logging.getLogger('scstatus')
logger.setLevel(logging.DEBUG)
# create file handler
#fh = logging.FileHandler('logs/scstatus.log')
#fh.setLevel(logging.DEBUG)
# create timedrotatingfilehandler
trfh = TimedRotatingFileHandler('logs/scstatus.log', when='d', interval=1, backupCount=14, encoding=None, delay=False, utc=False, atTime=None)
trfh.setLevel(logging.DEBUG)
# create console handler
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s')
#fh.setFormatter(formatter)
trfh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
#logger.addHandler(fh)
logger.addHandler(trfh)
logger.addHandler(ch)
# endregion init

def main():
    TESLA_CLIENT_ID = ""
    TESLA_CLIENT_SECRET = ""
    ACCESS_TOKEN = ""
    TWITTER_CONSUMER_KEY = ""
    TWITTER_CONSUMER_SECRET = ""
    TWITTER_ACCESS_TOKEN = ""
    TWITTER_ACCESS_TOKEN_SECRET = ""

    # Flag to turn on and off the waking logic
    WAKE_ENABLED = True

    with open("config.json", "r") as jsonfile:
        data = json.load(jsonfile)
        print("Read successful")
        TESLA_CLIENT_ID = data['TESLA_CLIENT_ID']
        TESLA_CLIENT_SECRET = data['TESLA_CLIENT_SECRET']
        ACCESS_TOKEN = data['ACCESS_TOKEN']
        TWITTER_CONSUMER_KEY = data['TWITTER_CONSUMER_KEY']
        TWITTER_CONSUMER_SECRET = data['TWITTER_CONSUMER_SECRET']
        TWITTER_ACCESS_TOKEN = data['TWITTER_ACCESS_TOKEN']
        TWITTER_ACCESS_TOKEN_SECRET = data['TWITTER_ACCESS_TOKEN_SECRET']

    service = OAuth2Service(
        client_id = TESLA_CLIENT_ID,
        client_secret = TESLA_CLIENT_SECRET,
        access_token_url = "https://owner-api.teslamotors.com/oauth/token",
        authorize_url = "https://owner-api.teslamotors.com/oauth/token",
        base_url = "https://owner-api.teslamotors.com/",
    )

    try:
        my_session = service.get_session(token=ACCESS_TOKEN)
        vehicle_list_url = "https://owner-api.teslamotors.com/api/1/vehicles/"
        vehicles_ret = my_session.get(vehicle_list_url)
        if vehicles_ret.status_code != 200:
            logger.error(f"Unexpected status code {vehicles_ret.status_code} for {vehicle_list_url}")
            return
        logger.debug(vehicles_ret.text)
        vehicles_json = vehicles_ret.json()
        vehicle_0_id = vehicles_json['response'][0]['id']
        vehicle_0_state = vehicles_json['response'][0]['state']

        # If car is asleep, we need to wake it
        if vehicle_0_state.lower() != "online":

            # Check whether to proceed with wake or just abort
            if not WAKE_ENABLED:
                logger.error("Car is not online but WAKE_ENABLED is also disabled")
                return

            # Wake it once
            logger.debug(f"Current state is {vehicle_0_state}")
            logger.info("Triggering a wake command")
            wake_url = f"https://owner-api.teslamotors.com/api/1/vehicles/{vehicle_0_id}/wake_up"
            wake_ret = my_session.post(wake_url)
            logger.debug(f"HTTP Code: {wake_ret.status_code}")

            # Wait until the car is awake
            counter = 0
            while counter < 10:

                # Sleep for 5 seconds
                logger.debug("Sleeping thread for 6s")
                time.sleep(6)
                logger.debug("Waking thread")
                vehicle_data_url = f"https://owner-api.teslamotors.com/api/1/vehicles/{vehicle_0_id}/vehicle_data"
                vehicle_data_ret = my_session.get(vehicle_data_url)

                # Don't abort even if this fails because car is in the middle of waking up
                if vehicle_data_ret.status_code != 200:
                    logger.error(f"Status code {vehicle_data_ret.status_code} for {vehicle_data_url}")
                else:
                    vehicle_data_json = vehicle_data_ret.json()
                    logger.debug(vehicle_data_json)
                    vehicle_0_state = vehicle_data_json['response']['state']

                # If the prev status check failed, state is the same
                logger.debug(f"Counter: {counter}, State: {vehicle_0_state}")
                if vehicle_0_state.lower() == "online":
                    logger.debug("Car is online. Continuing.")
                    break
                if counter >= 9:
                    logger.error("Failed to wake car up. Skipping run.")
                    return
                counter = counter + 1

        # Car should be awake at this point, so just go ahead and query for the nearby charging sites
        charging_sites_url = f"https://owner-api.teslamotors.com/api/1/vehicles/{vehicle_0_id}/nearby_charging_sites"
        charging_sites_ret = my_session.get(charging_sites_url)
        if charging_sites_ret.status_code != 200:
            logger.error(f"Unexpected status code {charging_sites_ret.status_code} for {charging_sites_url}")
            return
        logger.debug(charging_sites_ret.text)
        charging_sites_json = charging_sites_ret.json()
        superchargers_json = charging_sites_json['response']['superchargers']
        logger.debug(json.dumps(charging_sites_json, indent=4, sort_keys=True))
        logger.info("\n\n*Singapore SC Slots Free*")
        tweet_str = "Singapore SC Slots Free #TLKPSC\n"
        for supercharger in superchargers_json:
            logger.info(f"{supercharger['name']} : {supercharger['available_stalls']}/{supercharger['total_stalls']}")
            tweet_str += f"{supercharger['name']} : {supercharger['available_stalls']}/{supercharger['total_stalls']}\n"
        logger.info(f"Updated at {datetime.now().strftime('%d %b %Y %H:%M:%S')}")
        tweet_str += f"\nUpdated at {datetime.now().strftime('%d %b %Y %H:%M:%S')}"
        logger.info("\n")

        logger.debug(tweet_str)
    except:
        e = sys.exc_info()
        logger.error(e)
        logger.error(traceback.format_exc())
        return

    #twitter = Twython(
    #    TWITTER_CONSUMER_KEY,
    #    TWITTER_CONSUMER_SECRET,
    #    TWITTER_ACCESS_TOKEN,
    #    TWITTER_ACCESS_TOKEN_SECRET
    #)
    #twitter.update_status(status=tweet_str)

if __name__ == '__main__':
    main()