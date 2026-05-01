"""
WhatsApp Adapter - placeholder for future WhatsApp integration.
This demonstrates how the architecture supports multiple platforms.
"""

class WhatsAppAdapter:
    """
    Adapter for WhatsApp integration.
    
    Future implementation will:
    - Connect to WhatsApp Business API
    - Handle webhook events
    - Format messages for WhatsApp
    - Manage WhatsApp-specific features (buttons, lists, etc.)
    """
    
    def __init__(self):
        raise NotImplementedError("WhatsApp adapter not yet implemented")
    
    async def send_message(self, phone_number: str, message: str):
        """Send a message via WhatsApp."""
        pass
    
    async def handle_webhook(self, webhook_data: dict):
        """Process incoming WhatsApp webhook."""
        pass
