from odoo import models, fields, api
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ApiProduct(models.Model):
    _inherit = "api.product"

    def _get_reply_to_address(self):
        """Generate a reply-to address for this specific product record"""
        catchall_domain = (
            self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain")
        )
        return f"api_product-{self.id}@{catchall_domain}" if catchall_domain else False

    def _prepare_email_content(self, is_assigned_designer=True, designer_name=None):
        """Prepare email content with appropriate footers and tracking"""
        # Start with the original message body
        content = self.message_body

        # Add designer attribution footer if needed
        if not is_assigned_designer and designer_name:
            content += f"""
            <div style="margin-top: 15px; padding-top: 10px; border-top: 1px solid #ddd;">
                <small><i>This message was sent on behalf of {designer_name} (Assigned Designer)</i></small>
            </div>
            """

        # Add the approval options
        content += f"""
        <div style="margin-top: 20px; padding: 15px; border: 1px solid #ddd; background-color: #f9f9f9;">
            <p><strong>Please reply with one of the following options:</strong></p>
            <p>1. Approve - if you are satisfied with the design</p>
            <p>2. Develop and your design wishes - if the design needs further development</p>
        </div>
        """

        # Always add reference section for tracking
        content += f"""
        <div style="font-size:9px; color:#aaaaaa; margin-top:30px; border-top:1px solid #eeeeee; padding-top:5px;">
            Reference: Product {self.name} (ID: {self.id})
            <br/>Please keep this reference in your replies for better tracking.
        </div>
        """

        return content

    def action_send_message(self):
        """Send an email to the customer and log it in the chatter."""
        self.ensure_one()

        if not self.email:
            raise UserError("No customer email address found.")

        # Basic email validation
        if "@" not in self.email or "." not in self.email:
            raise UserError(
                "Invalid email format. Please provide a valid email address."
            )

        # Check permissions and roles
        current_user = self.env.user
        is_assigned_designer = (
            self.designer_id and self.designer_id.user_id.id == current_user.id
        )

        if not self.message_subject or not self.message_body:
            # If subject or body is empty, open the mail composer window
            return {
                "name": "Compose Message",
                "type": "ir.actions.act_window",
                "view_mode": "form",
                "res_model": "mail.compose.message",
                "target": "new",
                "context": {
                    "default_model": "api.product",
                    "default_res_id": self.id,
                    "default_email_to": self.email,
                    "default_subject": f"Re: {self.name}" if self.name else "",
                    "default_composition_mode": "comment",
                    "force_email": True,
                    "mail_notify_author": True,  # Don't notify the author
                    "mail_notify_force_send": True,  # Force send the email
                    "mail_create_nosubscribe": True,  # Don't subscribe recipients
                },
            }

        # Determine the appropriate sender
        if (
            self.designer_id
            and self.designer_id.user_id
            and self.designer_id.user_id.email
        ):
            sender_email = self.designer_id.user_id.email
            sender_name = self.designer_id.name
            designer_name = self.designer_id.name
        else:
            sender_email = current_user.email
            sender_name = current_user.name
            designer_name = current_user.name

        # Fallback to company email if needed
        if not sender_email:
            sender_email = self.env.company.email
            sender_name = self.env.company.name

        # Format sender and get reply-to address
        formatted_sender = (
            f"{sender_name} <{sender_email}>" if sender_name else sender_email
        )
        reply_to = self._get_reply_to_address() or formatted_sender

        # Prepare email content with appropriate footers
        modified_body = self._prepare_email_content(
            is_assigned_designer=is_assigned_designer, designer_name=designer_name
        )

        # Create and send email
        mail_values = {
            "subject": self.message_subject,
            "body_html": modified_body,
            "email_to": self.email,
            "email_from": formatted_sender,
            "reply_to": reply_to,
            "model": "api.product",
            "res_id": self.id,
            "auto_delete": False,
            "headers": {
                "X-Odoo-Object-Id": str(self.id),
                "X-Odoo-Object-Model": "api.product",
            },
        }

        _logger.info(f"Sending email to external recipient {self.email}")
        mail = self.env["mail.mail"].sudo().create(mail_values)
        mail.send()

        # Check if we should skip notifying followers (from context)
        skip_followers = self.env.context.get("skip_followers", True)

        # Log in chatter
        self.message_post(
            body=modified_body,
            subject=self.message_subject,
            message_type="email",
            subtype_xmlid="mail.mt_comment",
            email_layout_xmlid="mail.mail_notification_light",
            mail_auto_delete=False,
            partner_ids=(
                [] if skip_followers else None
            ),  # Empty list means no partners are notified
        )

        # Clear the form fields
        self.write(
            {
                "message_subject": False,
                "message_body": False,
            }
        )

        # Prepare success message
        success_message = f"Email sent to {self.email}"
        if not is_assigned_designer and self.designer_id:
            success_message = f"Email sent to {self.email} on behalf of {designer_name}"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Success",
                "message": success_message,
                "sticky": False,
                "type": "success",
            },
        }

    def manage_followers(self):
        """Add customer email as a follower and remove Administrator from followers"""
        self.ensure_one()

        if not self.customer_email:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "No Customer Email",
                    "message": "No customer email found to add as follower.",
                    "type": "warning",
                },
            }

        # Find Administrator partner
        admin_partner = self.env.ref("base.partner_admin", False)

        # Find or create partner for customer email
        partner_obj = self.env["res.partner"]
        customer_partner = partner_obj.search(
            [("email", "=", self.customer_email)], limit=1
        )

        if not customer_partner:
            # Create a new partner for this email
            customer_name = (
                self.email.split("@")[0] if "@" in self.customer_email else "Customer"
            )
            customer_partner = partner_obj.create(
                {
                    "name": customer_name,
                    "email": self.customer_email,
                }
            )

        # Add customer as follower if not already
        if customer_partner:
            if customer_partner.id not in self.message_partner_ids.ids:
                self.message_subscribe(partner_ids=[customer_partner.id])

        # Remove Administrator from followers if present
        if admin_partner and admin_partner.id in self.message_partner_ids.ids:
            self.message_unsubscribe(partner_ids=[admin_partner.id])

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Followers Updated",
                "message": f"Added {self.customer_email} as follower and removed Administrator.",
                "sticky": False,
                "type": "success",
            },
        }

    @api.model
    def create(self, vals):
        """Override create to auto-manage followers when record is created"""
        record = super(ApiProduct, self).create(vals)
        # Automatically manage followers if customer_email is present
        if record.customer_email:
            # Call in sudo to ensure we have permissions to modify followers
            record.sudo()._auto_manage_followers()
        return record

    def write(self, vals):
        """Override write to auto-manage followers when customer_email is updated"""
        result = super(ApiProduct, self).write(vals)
        # If customer_email is updated, manage followers
        if "customer_email" in vals and vals.get("customer_email"):
            for record in self:
                record.sudo()._auto_manage_followers()
        return result

    def _auto_manage_followers(self):
        """Automatically add customer as follower and remove Administrator"""
        self.ensure_one()

        if not self.customer_email:
            return

        # Find Administrator partner
        admin_partner = self.env.ref("base.partner_admin", False)

        # Find or create partner for customer email
        partner_obj = self.env["res.partner"]
        customer_partner = partner_obj.search(
            [("email", "=", self.customer_email)], limit=1
        )

        if not customer_partner:
            # Create a new partner for this email
            customer_name = (
                self.customer_email.split("@")[0]
                if "@" in self.customer_email
                else "Customer"
            )
            customer_partner = partner_obj.create(
                {
                    "name": customer_name,
                    "email": self.customer_email,
                }
            )

        # Add customer as follower if not already
        if customer_partner:
            if customer_partner.id not in self.message_partner_ids.ids:
                self.message_subscribe(partner_ids=[customer_partner.id])

        # Remove Administrator from followers if present
        if admin_partner and admin_partner.id in self.message_partner_ids.ids:
            self.message_unsubscribe(partner_ids=[admin_partner.id])

    def _process_email_content(self, body):
        """Process email body content and update record state accordingly."""
        _logger.info(f"Processing email content: {body[:100]}...")

        # Extract only the reply part (before any quoted content)
        # First try to find standard Gmail/Outlook style quoted content
        reply_text = body

        # Look for common quote markers
        quote_markers = [
            "<div data-o-mail-quote",
            "<blockquote",
            "On .* wrote:",
            "---Original Message---",
            "------ Reply Message ------",
            "________________________________",
        ]

        for marker in quote_markers:
            import re

            match = re.search(marker, body, re.IGNORECASE | re.DOTALL)
            if match:
                reply_text = body[: match.start()]
                _logger.info(
                    f"Found quote marker '{marker}', extracting only reply: {reply_text}"
                )
                break

        # Now check only the actual reply text for keywords
        reply_text = reply_text.lower()
        _logger.info(
            f"Checking reply portion for approval/development keywords: {reply_text}"
        )

        self.write(
            {
                "unread_messages": True,
            }
        )

        if "1" in reply_text or "approve" in reply_text or "agreed" in reply_text:
            # Customer approved the design - change state to done
            _logger.info(f"Customer approved design for product {self.id}")
            self.write(
                {
                    "state": "done",
                }
            )

            # Add system message about state change
            self.message_post(
                body="<strong>Customer approved the design</strong><br/>Status changed to Done.",
                message_type="notification",
                subtype_xmlid="mail.mt_note",
            )

        elif (
            "2" in reply_text
            or "develop" in reply_text
            or "change" in reply_text
            or "need" in reply_text
            or "adjust" in reply_text
        ):
            # Customer requested further development - change state to processing
            _logger.info(
                f"Customer requested further development for product {self.id}"
            )
            self.write(
                {
                    "state": "processing",
                }
            )

            # Add system message about state change
            self.message_post(
                body="<strong>Customer requested further development</strong><br/>Status changed to Processing.",
                message_type="notification",
                subtype_xmlid="mail.mt_note",
            )

        # Notify assigned designer with internal message if assigned
        if self.designer_id and self.designer_id.user_id:
            _logger.warning(
                f"Notifying assigned designer {self.designer_id.name} about the email reply"
            )

            # Use the new messaging utility
            message_util = self.env["inventory_button.send_message"]
            message_util.notify_customer_reply(self)

        return True

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """Process incoming emails and create new records if needed or update existing ones."""
        # Try to extract product ID from the reply-to or email references
        product_id = None
        email_to = msg_dict.get("to", "")

        if "api_product-" in email_to:
            # Extract ID from reply-to format: api_product-ID@domain
            try:
                product_id = int(email_to.split("api_product-")[1].split("@")[0])
                _logger.info(f"Extracted product ID from email_to: {product_id}")
            except (IndexError, ValueError):
                _logger.warning(
                    f"Could not extract product ID from email_to: {email_to}"
                )

        # If we found a product ID, update that record
        if product_id:
            try:
                product = self.browse(product_id)
                if product.exists():
                    # Process email body content
                    body = msg_dict.get("body", "").lower()
                    product._process_email_content(body)

                    # Update the existing record with the email reply (always post the email)
                    _logger.info(
                        f"Found existing product with ID {product_id}, updating with email reply"
                    )
                    product.message_post(
                        body=msg_dict.get("body"),
                        subject=msg_dict.get("subject"),
                        message_type="email",
                        subtype_xmlid="mail.mt_comment",
                        email_from=msg_dict.get("from"),
                        author_id=msg_dict.get("author_id"),
                    )
                    return product
            except Exception as e:
                _logger.error(
                    f"Error when processing email for product {product_id}: {str(e)}"
                )

        # If no product ID found or product doesn't exist, return None
        _logger.warning("Could not match email to an existing product, ignoring")
        return None

    @api.model
    def message_update(self, msg_dict, update_vals=None):
        """Override message_update to handle incoming emails for existing records."""
        _logger.info(f"sigma message email with subject: {msg_dict.get('subject')}")
        _logger.info(
            f"message info: to={msg_dict.get('to')}, from={msg_dict.get('from')}, thread_id={msg_dict.get('thread_id')}"
        )

        # Get email body content and process it
        body = msg_dict.get("body", "").lower()
        self._process_email_content(body)

        # Call the original message_update method
        return super(ApiProduct, self).message_update(msg_dict, update_vals=update_vals)

    def message_post(self, **kwargs):
        """Override message_post to add approval options to messages sent from standard chatter"""
        # Only add approval options if this is an email message being sent to customers
        if (
            kwargs.get("message_type") == "email"
            or kwargs.get("subtype_xmlid") == "mail.mt_comment"
        ):
            # Get the original body
            body = kwargs.get("body", "")

            # Add the approval options if not already present
            if "Please reply with one of the following options" not in body:
                approval_options = f"""
                <div style="margin-top: 20px; padding: 15px; border: 1px solid #ddd; background-color: #f9f9f9;">
                    <p><strong>Please reply with one of the following options:</strong></p>
                    <p>1. Approve - if you are satisfied with the design</p>
                    <p>2. Develop - if the design needs further development</p>
                </div>
                """

                # Insert the approval options before any reference or signature section
                if "Reference:" in body:
                    # Insert before the reference section
                    reference_pos = body.find("Reference:")
                    div_pos = body.rfind("<div", 0, reference_pos)

                    if div_pos != -1:
                        kwargs["body"] = (
                            body[:div_pos] + approval_options + body[div_pos:]
                        )
                    else:
                        kwargs["body"] = body + approval_options
                else:
                    # Append to the end of the body
                    kwargs["body"] = body + approval_options

        # Call the original method with our modified kwargs
        return super(ApiProduct, self).message_post(**kwargs)
