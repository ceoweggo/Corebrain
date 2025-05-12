"""
Utilidades de serialización para Corebrain SDK.
"""
import json

from datetime import datetime, date, time
from bson import ObjectId
from decimal import Decimal

class JSONEncoder(json.JSONEncoder):
    """Serializador JSON personalizado para tipos especiales."""
    def default(self, obj):
        # Objetos datetime
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
        # Objetos timedelta
        elif hasattr(obj, 'total_seconds'):  # Para objetos timedelta
            return obj.total_seconds()
        # ObjectId de MongoDB
        elif isinstance(obj, ObjectId):
            return str(obj)
        # Bytes o bytearray
        elif isinstance(obj, (bytes, bytearray)):
            return obj.hex()
        # Decimal
        elif isinstance(obj, Decimal):
            return float(obj)
        # Otros tipos
        return super().default(obj)

def serialize_to_json(obj):
    """Serializa cualquier objeto a JSON usando el encoder personalizado"""
    return json.dumps(obj, cls=JSONEncoder)