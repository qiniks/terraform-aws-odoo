from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SendMessage(models.AbstractModel):
    _name = "inventory_button.send_message"
    _description = "Messaging Utility for Inventory Button"

    @api.model
    def send_notification(
        self, partner, title, message, sticky=False, message_type="info"
    ):
        """
        Send a notification to a specific partner via the bus channel.

        Args:
            partner: The res.partner record to send notification to
            title: The title of the notification
            message: The body message of the notification
            sticky: Whether the notification should stay until dismissed
            message_type: Type of message (info, success, warning, danger)

        Returns:
            bool: True if notification was sent
        """
        _logger.info(f"Sending notification to {partner.name}: {title} - {message}")

        try:
            self.env["bus.bus"]._sendone(
                partner,
                "simple_notification",
                {
                    "title": title,
                    "message": message,
                    "sticky": sticky,
                    "type": message_type,
                },
            )
            return True
        except Exception as e:
            _logger.error(f"Failed to send notification: {e}")
            return False

    @api.model
    def notify_customer_reply(self, record, type="info"):
        """
        Send notification about new customer reply to the assigned designer.

        Args:
            record: The record (e.g. api.product) that received a customer reply

        Returns:
            bool: True if notification was sent, False otherwise
        """
        if not record or not record.designer_id or not record.name:
            _logger.warning(
                "Cannot send notification: missing record, designer_id or name"
            )
            return False

        if not record.designer_id.user_id or not record.designer_id.user_id.partner_id:
            _logger.warning(
                "Cannot send notification: designer has no associated user or partner"
            )
            return False

        notification_message = f"New customer reply received for product {record.name}"
        return self.send_notification(
            record.designer_id.user_id.partner_id,
            "Customer Reply",
            notification_message,
            sticky=True,
            message_type=type,
        )
