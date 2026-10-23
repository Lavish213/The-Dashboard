from uuid import UUID

from services.connection_status import source_tenant


def validate_delivery_overview(data):
    if type(data.get('schema_version')) is not int or data['schema_version'] != 1 or data.get('tenant_id') != source_tenant():
        raise ValueError('Unbound delivery evidence')
    journal = data.get('journal')
    messages = data.get('messages')
    if not isinstance(journal, dict) or not isinstance(messages, list) or len(messages) > 100:
        raise ValueError('Bounded delivery evidence required')
    for key in ('pending', 'received', 'oldest_pending_seconds'):
        if type(journal.get(key)) is not int or journal[key] < 0:
            raise ValueError('Invalid delivery journal')
    safe = []
    for message in messages:
        if not isinstance(message, dict) or message.get('channel') not in {'sms', 'email'} or message.get('delivery_status') not in {'pending', 'delivered', 'failed', 'conflicting_receipts', 'unknown'}:
            raise ValueError('Invalid provider receipt')
        for flag in ('opened', 'clicked', 'suppressed'):
            if type(message.get(flag)) is not bool:
                raise ValueError('Invalid receipt flags')
        lead = str(UUID(message['lead_id'])) if message.get('lead_id') else None
        identity = message.get('intent_id')
        if not isinstance(identity, str) or len(identity) != 64 or any(c not in '0123456789abcdef' for c in identity):
            raise ValueError('Invalid message identity')
        safe.append({'intent_id': identity, 'lead_id': lead, 'channel': message['channel'], 'delivery_status': message['delivery_status'], **{key: message[key] for key in ('opened', 'clicked', 'suppressed')}})
    return {'schema_version': 1, 'inventory': validate_inventory(data.get('inventory')), 'journal': {key: journal[key] for key in ('pending', 'received', 'oldest_pending_seconds')}, 'messages': safe, 'limit': 100}


def validate_inventory(inventory):
    if inventory is None:
        return None
    if not isinstance(inventory, dict):
        raise ValueError('Invalid message inventory')
    keys = ('accepted', 'uncertain_submission', 'pending_projection')
    if any(type(inventory.get(key)) is not int or inventory[key] < 0 for key in keys):
        raise ValueError('Invalid inventory counts')
    return {key: inventory[key] for key in keys}
