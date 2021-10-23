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
import websocket
import _thread

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

ACCESS_TOKEN = ""
VEHICLE_ID = ""
STREAMING = False

def on_message(ws, message):
    logger.debug(message)
    
    # If we get any update message, it is a sign that car is still active
    if "data:update" in message.decode():
        global STREAMING
        STREAMING = True

def on_error(ws, error):
    logger.debug(error)

def on_close(ws):
    logger.debug("### closed ###")

def on_open(ws):
    def run(*args):
        connect_msg = {
            "msg_type":"data:subscribe_oauth",
            "token":ACCESS_TOKEN,
            "value":"speed,odometer,soc,elevation,est_heading,est_lat,est_lng,power,shift_state,range,est_range,heading",
            "tag":VEHICLE_ID
        }
        logger.debug(f"Sending {json.dumps(connect_msg).encode()}")
        ws.send(json.dumps(connect_msg).encode())
        logger.debug("Waiting for 20 secs for update messages")
        time.sleep(20)
        ws.close()
        logger.debug("thread terminating...")
    _thread.start_new_thread(run, ())



def main():
    TESLA_CLIENT_ID = ""
    TESLA_CLIENT_SECRET = ""
    global ACCESS_TOKEN
    TWITTER_CONSUMER_KEY = ""
    TWITTER_CONSUMER_SECRET = ""
    TWITTER_ACCESS_TOKEN = ""
    TWITTER_ACCESS_TOKEN_SECRET = ""

    # Flag to turn on and off the waking logic
    WAKE_ENABLED = False

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
        global VEHICLE_ID
        VEHICLE_ID = f"{vehicles_json['response'][0]['vehicle_id']}"
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
                    logger.debug(f"Status code {vehicle_data_ret.status_code} for {vehicle_data_url}")
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

        # Additional check so we don't wake up the car if it is trying to sleep.
        # If streaming websocket gives any update data, that means car is still active (driving/sentry or it just performed some action via API)
        # Need to conduct more tests to see how soon car will try to sleep after calling nearby_charging_sites
        websocket.enableTrace(True)
        ws = websocket.WebSocketApp("wss://streaming.vn.teslamotors.com/streaming/", on_close = on_close, on_error = on_error, on_message = on_message, on_open = on_open)
        ws.run_forever()

        if STREAMING:
            logger.debug("Returned from websocket and car is still awake.")

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

        else:
            logger.debug("Returned from websocket and car is trying to sleep. Don't disturb it.")

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