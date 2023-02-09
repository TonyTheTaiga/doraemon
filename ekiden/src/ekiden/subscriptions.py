import asyncio
import logging
from typing import MutableSet, Optional

from starlette.websockets import WebSocket

from ekiden.nips import ETag, Event, Filters, PTag, dump_json

logger = logging.getLogger(__name__)


def validate_scalar(candidates, subject) -> bool:
    """
    For scalar event attributes such as kind, the attribute from the event must be contained in the filter list
    """
    if len(candidates) == 0:
        return True

    return True if subject in candidates else False


def validate_multiple(candidates, subjects) -> bool:
    """
    For tag attributes such as #e, where an event may have multiple values, the event and filter condition values must have at least one item in common.
    """
    a = set(candidates)
    b = set(subjects)
    if len(a) == 0:
        return True

    return len(a.intersection(b)) > 0


def validate_since(candidate, subject) -> bool:
    if candidate is None:
        return True

    return subject > candidate


def validate_until(candidate, subject) -> bool:
    if candidate is None:
        return True

    return subject < candidate


def validate_filters(event: Event, filters: Filters) -> bool:
    """Given a event, validate the filters on it.

    Args:
        event (Event): The event under question
        filters (Filters): The filter to validate

    Returns:
        bool: True if the event passes the filters, else False.
    """
    if (
        validate_scalar(filters.ids, event.id)
        and validate_scalar(filters.authors, event.pubkey)
        and validate_scalar(filters.kinds, event.kind)
        and validate_multiple(filters.event_ids, [tag.id for tag in event.tags if isinstance(tag, ETag)])
        and validate_multiple(filters.pubkeys, [tag.pubkey for tag in event.tags if isinstance(tag, PTag)])
        and validate_since(filters.since, event.created_at)
        and validate_until(filters.until, event.created_at)
    ):
        return True
    return False


class Subscription:
    def __init__(self, filters: Filters, websocket: WebSocket, subscription_id: str):
        self.filters = filters
        self.websocket = websocket
        self.subscription_id = subscription_id

    async def send(self, event: Event):
        if validate_filters(event, self.filters):
            await self.websocket.send_text(dump_json(["EVENT", self.subscription_id, event.dict()]))


class SubscriptionPool:
    def __init__(self) -> None:
        self._subscriptions: MutableSet[Subscription] = set()
        self._access_lock = asyncio.Lock()

    async def get_subscription(self, websocket: WebSocket) -> Optional[Subscription]:
        """Retrieve a subscription from the pool with the matching websocket.

        Args:
            websocket (WebSocket): The websocket to match

        Returns:
            Optional[Subscription]: The matching subscription if found, else None.
        """
        async with self._access_lock:
            for subscription in self._subscriptions:
                if subscription.websocket == websocket:
                    return subscription

            return None

    async def add_subscription(self, subscription: Subscription):
        """Add a new subscription to the pool

        Args:
            subscription (Subscription): The subscription to add
        """
        async with self._access_lock:
            self._subscriptions.add(subscription)

    async def remove_subscription(self, subscription: Subscription):
        """Remove the subscription from the pool

        Args:
            subscription (Subscription): The subscription to remove
        """
        logger.info(f"Removing subscription: {subscription.subscription_id}")
        async with self._access_lock:
            self._subscriptions.discard(subscription)

    async def broadcast(self, event: Event):
        """Broadcasts the event to all subscribers.
        The subscriber will only receive the message if the event passes the filters.

        Args:
            event (Event): The event to broadcast
        """
        _stale = []

        async with self._access_lock:
            for subscription in self._subscriptions:
                try:
                    await subscription.send(event)
                except RuntimeError:
                    _stale.append(subscription)

            [await self.remove_subscription(subscription) for subscription in _stale]
