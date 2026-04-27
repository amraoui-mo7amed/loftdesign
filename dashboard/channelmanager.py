"""
Custom channel manager for django-eventstream.
Ensures users can only read their own notification channels.
"""

import logging

from django_eventstream.channelmanager import DefaultChannelManager

logger = logging.getLogger(__name__)


class NotificationChannelManager(DefaultChannelManager):
    """
    Channel manager that restricts access to user-specific channels.

    Channel format: user-{user_id}
    Only authenticated users can access their own user-{user_id} channel.
    """

    def can_read_channel(self, user, channel):
        """
        Check if user has permission to read from a channel.

        Args:
            user: The authenticated user (None if not authenticated)
            channel: The channel name

        Returns:
            bool: True if user can read from this channel
        """
        # Superusers can read any channel (for debugging)
        if user and user.is_superuser:
            return True

        # Channel must start with "user-" prefix
        if not channel.startswith("user-"):
            # Deny access to non-user channels
            logger.warning(
                f"Access denied: Channel '{channel}' does not start with 'user-'"
            )
            return False

        # User must be authenticated
        if user is None:
            logger.warning(
                f"Access denied: Anonymous user trying to access channel '{channel}'"
            )
            return False

        # Extract user_id from channel name
        try:
            channel_user_id = int(channel.split("-")[1])
        except (IndexError, ValueError):
            logger.warning(f"Access denied: Invalid channel format '{channel}'")
            return False

        # User can only read their own channel
        if user.id == channel_user_id:
            logger.info(
                f"Access granted: User {user.username} accessing channel '{channel}'"
            )
            return True

        # User trying to access another user's channel
        logger.warning(
            f"Access denied: User {user.username} (ID: {user.id}) tried to access channel '{channel}' "
            f"which belongs to user ID {channel_user_id}"
        )
        return False