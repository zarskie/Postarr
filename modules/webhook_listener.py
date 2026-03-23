from concurrent.futures import ThreadPoolExecutor

from flask import Flask, request

from main import get_config, logger, run_renamer

cli_app = Flask(__name__)

config = get_config(logger)
executor = ThreadPoolExecutor(max_workers=3)


def run_renamer_task(config, new_item):
    try:
        run_renamer(config, new_item)
    except Exception as e:
        logger.error(f"Error in run_renamerr: {e}", exc_info=True)


@cli_app.route("/arr-webhook", methods=["POST"])
def recieve_webhook():
    from main import db

    data = request.json
    if not data:
        logger.error("No data recieved in the webhook")
        return "No data recieved", 400

    valid_event_types = ["Download", "Grab", "MovieAdded", "SeriesAdd"]
    webhook_event_type = data.get("eventType", "")

    if webhook_event_type == "Test":
        logger.info("Test event recived successfully")
        return "OK", 200

    if webhook_event_type not in valid_event_types:
        logger.debug(f"'{webhook_event_type}' is not a valid event type")
        return "Invalid event type", 400

    logger.info(f"Processing event type: {webhook_event_type}")
    try:
        item_type = (
            "movie" if "movie" in data else "series" if "series" in data else None
        )
        if not item_type:
            logger.error("Neither 'movie' nor 'series' found in webhook data")
            return "Invalid webhook data", 400
        id = data.get(item_type, {}).get("id", None)
        id = int(id)
        if not id:
            logger.error(f"Item ID not found for {item_type} in webhook data")
            return "Invalid webhook data", 400
        instance = data.get("instanceName", "").lower()
        if not instance:
            logger.error(
                "Instance name missing from webhook data, please configure in arr settings."
            )
            return "Invalid webhook data", 400

        item_path = None

        if item_type == "movie":
            item_path = data.get(item_type, {}).get("folderPath", None)
        elif item_type == "series":
            item_path = data.get(item_type, {}).get("path", None)

        if not item_path:
            logger.error("Item path missing from webhook data")
            return "Invalid webhook data", 400

        new_item = {
            "type": item_type,
            "item_id": id,
            "instance_name": instance,
            "item_path": item_path,
        }

        is_duplicate = db.is_duplicate_webhook(new_item)

        if is_duplicate:
            logger.debug(f"Duplicate webhook detected: {new_item}")
        else:
            logger.debug(f"Extracted item: {new_item}")
            executor.submit(run_renamer_task, config, new_item)

    except Exception as e:
        logger.error(f"Error retrieving single item from webhook: {e}", exc_info=True)
        return "Internal server error", 500

    return "OK", 200
