# import json
# import logging
# import os

# import paho.mqtt.client as mqtt
# from django.conf import settings
# from django.core.management.base import BaseCommand

# logger = logging.getLogger(__name__)

# MQTT_HOST = getattr(settings, "MQTT_BROKER_HOST", "localhost")
# MQTT_PORT = getattr(settings, "MQTT_BROKER_PORT", 1883)
# MQTT_USERNAME = getattr(settings, "MQTT_USERNAME", "")
# MQTT_PASSWORD = getattr(settings, "MQTT_PASSWORD", "")
# MQTT_USE_TLS = getattr(settings, "MQTT_USE_TLS", False)
# MQTT_TOPIC_PREFIX = getattr(settings, "MQTT_TOPIC_PREFIX", "ondra/production")


# class Command(BaseCommand):
#     help = "Starts the MQTT subscriber that processes RFID gate events"

#     def handle(self, *args, **options):
#         self.stdout.write("Starting Ondra MQTT subscriber...")

#         client = mqtt.Client(
#             client_id="ondra-django-subscriber",
#             clean_session=False,
#         )

#         if MQTT_USERNAME:
#             client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

#         if MQTT_USE_TLS:
#             client.tls_set()

#         client.on_connect = self._on_connect
#         client.on_message = self._on_message
#         client.on_disconnect = self._on_disconnect

#         try:
#             client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
#             self.stdout.write(
#                 self.style.SUCCESS(
#                     f"Connected to MQTT broker at {MQTT_HOST}:{MQTT_PORT}"
#                 )
#             )
#             # Blocking loop — runs forever until interrupted
#             client.loop_forever()
#         except KeyboardInterrupt:
#             self.stdout.write("\nShutting down MQTT subscriber.")
#             client.disconnect()
#         except Exception as e:
#             raise SystemExit(f"MQTT connection failed: {e}") from e

#     def _on_connect(self, client, userdata, flags, rc):
#         if rc == 0:
#             # Subscribe to all event types across all terminals and readers
#             topics = [
#                 (f"{MQTT_TOPIC_PREFIX}/+/+/tag_detected", 1),
#                 (f"{MQTT_TOPIC_PREFIX}/+/+/heartbeat", 1),
#                 (f"{MQTT_TOPIC_PREFIX}/+/+/alert", 1),
#             ]
#             client.subscribe(topics)
#             logger.info("MQTT subscriber connected and subscribed")
#             self.stdout.write(self.style.SUCCESS("Subscribed to all RFID topics"))
#         else:
#             logger.error(f"MQTT connection failed with code {rc}")

#     def _on_disconnect(self, client, userdata, rc):
#         if rc != 0:
#             logger.warning(f"Unexpected MQTT disconnect — code {rc}. Will auto-reconnect.")

#     def _on_message(self, client, userdata, msg):
#         try:
#             topic = msg.topic
#             payload = json.loads(msg.payload.decode("utf-8"))
#             event_type = topic.split("/")[-1]

#             logger.debug(f"Received {event_type} on {topic}")

#             if event_type == "tag_detected":
#                 self._handle_tag_detected(payload)
#             elif event_type == "heartbeat":
#                 self._handle_heartbeat(payload)
#             elif event_type == "alert":
#                 self._handle_hardware_alert(payload)

#         except json.JSONDecodeError:
#             logger.error(f"Invalid JSON payload on topic {msg.topic}")
#         except Exception as e:
#             logger.error(f"Error processing MQTT message: {e}", exc_info=True)

#     def _handle_tag_detected(self, payload: dict):
#         """
#         Processes a tag_detected event.
#         Calls process_rfid_event_service synchronously since paho-mqtt
#         callbacks are synchronous.
#         """
#         from asgiref.sync import async_to_sync
#         from rfid.schemas import RFIDEventInSchema
#         from rfid.services import process_rfid_event_service
#         from terminals.models import Terminals

#         try:
#             terminal_id = payload.get("terminal_id")
#             gate_id = payload.get("reader_id")

#             # Resolve organization from terminal
#             terminal = Terminals.objects.select_related(
#                 "organization"
#             ).get(id=terminal_id)
#             organization_id = terminal.organization_id

#             event_data = RFIDEventInSchema(
#                 message_id=payload["message_id"],
#                 raw_tag_id=payload["tag_id"],
#                 gate_id=gate_id,
#                 terminal_id=terminal_id,
#                 direction=payload["direction"],
#                 signal_strength=payload.get("signal_strength"),
#                 event_time=payload["timestamp"],
#             )

#             result = async_to_sync(process_rfid_event_service)(
#                 event_data, organization_id
#             )
#             logger.info(
#                 f"Processed tag event: {payload['tag_id']} "
#                 f"— recognized: {result.is_recognized}"
#             )

#         except Terminals.DoesNotExist:
#             logger.error(f"Terminal not found for id: {payload.get('terminal_id')}")
#         except Exception as e:
#             logger.error(f"Error handling tag_detected: {e}", exc_info=True)

#     def _handle_heartbeat(self, payload: dict):
#         """
#         Updates RFIDReaderStatus on heartbeat receipt.
#         Creates the record if it does not exist.
#         """
#         from django.utils import timezone
#         from rfid.models import RFIDReaderStatus
#         from terminals.models import Gates

#         try:
#             reader_id = payload.get("reader_id")
#             terminal_id = payload.get("terminal_id")
#             status = payload.get("status", "online")

#             terminal = __import__(
#                 "terminals.models", fromlist=["Terminals"]
#             ).Terminals.objects.get(id=terminal_id)

#             RFIDReaderStatus.objects.update_or_create(
#                 reader_id=reader_id,
#                 defaults={
#                     "terminal_id": terminal_id,
#                     "organization_id": terminal.organization_id,
#                     "status": status,
#                     "firmware_version": payload.get("firmware_version"),
#                     "uptime_seconds": payload.get("uptime_seconds"),
#                     "last_heartbeat": timezone.now(),
#                 },
#             )
#             logger.debug(f"Heartbeat updated for reader: {reader_id}")

#         except Exception as e:
#             logger.error(f"Error handling heartbeat: {e}", exc_info=True)

#     def _handle_hardware_alert(self, payload: dict):
#         """
#         Logs hardware fault alerts from RFID readers.
#         Creates a notification for the terminal head.
#         """
#         logger.warning(
#             f"Hardware alert from reader {payload.get('reader_id')}: "
#             f"{payload.get('alert_type')} — {payload.get('description')}"
#         )
#         # TODO: create notification record and push WebSocket alert
#         # to terminal head when notification module is built

import asyncio
import json
import logging
import signal

import gmqtt
from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

MQTT_HOST = getattr(settings, "MQTT_BROKER_HOST", "localhost")
MQTT_PORT = getattr(settings, "MQTT_BROKER_PORT", 1883)
MQTT_USERNAME = getattr(settings, "MQTT_USERNAME", "")
MQTT_PASSWORD = getattr(settings, "MQTT_PASSWORD", "")
MQTT_USE_TLS = getattr(settings, "MQTT_USE_TLS", False)
MQTT_TOPIC_PREFIX = getattr(settings, "MQTT_TOPIC_PREFIX", "ondra/production")


class Command(BaseCommand):
    help = "Starts the MQTT subscriber (gmqtt -> Mosquitto) that processes RFID gate events"

    def handle(self, *args, **options):
        self.stdout.write("Starting Ondra MQTT subscriber...")
        try:
            asyncio.run(self._run())
        except KeyboardInterrupt:
            self.stdout.write("\nShutting down MQTT subscriber.")

    async def _run(self):
        client = gmqtt.Client("ondra-django-subscriber", clean_session=False)

        if MQTT_USERNAME:
            client.set_auth_credentials(MQTT_USERNAME, MQTT_PASSWORD)

        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.on_disconnect = self._on_disconnect

        stop = asyncio.Event()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)

        ssl_ctx = True if MQTT_USE_TLS else None
        await client.connect(MQTT_HOST, MQTT_PORT, ssl=ssl_ctx, keepalive=60)

        await stop.wait()
        await client.disconnect()

    def _on_connect(self, client, flags, rc, properties):
        topics = [
            f"{MQTT_TOPIC_PREFIX}/+/+/tag_detected",
            f"{MQTT_TOPIC_PREFIX}/+/+/heartbeat",
            f"{MQTT_TOPIC_PREFIX}/+/+/alert",
        ]
        for topic in topics:
            client.subscribe(topic, qos=1)
        logger.info("MQTT subscriber connected and subscribed")
        self.stdout.write(self.style.SUCCESS("Subscribed to all RFID topics"))

    def _on_disconnect(self, client, packet, exc=None):
        logger.warning("MQTT disconnected. gmqtt will auto-reconnect.")

    def _on_message(self, client, topic, payload, qos, properties):
        # gmqtt calls on_message synchronously; schedule async handling
        asyncio.create_task(self._process_message(topic, payload))

    async def _process_message(self, topic: str, raw_payload: bytes):
        try:
            payload = json.loads(raw_payload.decode("utf-8"))
            event_type = topic.split("/")[-1]

            logger.debug(f"Received {event_type} on {topic}")

            if event_type == "tag_detected":
                await self._handle_tag_detected(payload)
            elif event_type == "heartbeat":
                await self._handle_heartbeat(payload)
            elif event_type == "alert":
                await self._handle_hardware_alert(payload)

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON payload on topic {topic}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}", exc_info=True)

    async def _handle_tag_detected(self, payload: dict):
        """
        Processes a tag_detected event. Now natively async — no
        async_to_sync gymnastics needed since we're already in an
        asyncio event loop.
        """
        from rfid_events.schema import RFIDEventInSchema
        from rfid_events.services import process_rfid_event_service
        from terminals.models import Terminals

        try:
            terminal_id = payload.get("terminal_id")
            gate_id = payload.get("reader_id")

            terminal = await Terminals.objects.select_related(
                "organization"
            ).aget(id=terminal_id)
            organization_id = terminal.organization_id

            event_data = RFIDEventInSchema(
                message_id=payload["message_id"],
                raw_tag_id=payload["tag_id"],
                gate_id=gate_id,
                terminal_id=terminal_id,
                direction=payload["direction"],
                signal_strength=payload.get("signal_strength"),
                event_time=payload["timestamp"],
            )

            result = await process_rfid_event_service(event_data, organization_id)
            logger.info(
                f"Processed tag event: {payload['tag_id']} "
                f"— recognized: {result.is_recognized}"
            )

        except Terminals.DoesNotExist:
            logger.error(f"Terminal not found for id: {payload.get('terminal_id')}")
        except Exception as e:
            logger.error(f"Error handling tag_detected: {e}", exc_info=True)

    async def _handle_heartbeat(self, payload: dict):
        """
        Updates RFIDReaderStatus on heartbeat receipt.
        Creates the record if it does not exist.
        """
        from django.utils import timezone
        from rfid_events.models import RFIDReaderStatus
        from terminals.models import Terminals

        try:
            reader_id = payload.get("reader_id")
            terminal_id = payload.get("terminal_id")
            status = payload.get("status", "online")

            terminal = await Terminals.objects.aget(id=terminal_id)

            await RFIDReaderStatus.objects.aupdate_or_create(
                reader_id=reader_id,
                defaults={
                    "terminal_id": terminal_id,
                    "organization_id": terminal.organization_id,
                    "status": status,
                    "firmware_version": payload.get("firmware_version"),
                    "uptime_seconds": payload.get("uptime_seconds"),
                    "last_heartbeat": timezone.now(),
                },
            )
            logger.debug(f"Heartbeat updated for reader: {reader_id}")

        except Exception as e:
            logger.error(f"Error handling heartbeat: {e}", exc_info=True)

    async def _handle_hardware_alert(self, payload: dict):
        """
        Logs hardware fault alerts from RFID readers.
        Creates a notification for the terminal head.
        """
        logger.warning(
            f"Hardware alert from reader {payload.get('reader_id')}: "
            f"{payload.get('alert_type')} — {payload.get('description')}"
        )
        # TODO: create notification record and push WebSocket alert
        # to terminal head when notification module is built
