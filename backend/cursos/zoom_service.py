import jwt
import time
from datetime import datetime, timedelta
from decouple import config

class ZoomService:
    @staticmethod
    def generate_signature(session_name, role=1):
        """
        Genera un JWT token para Zoom Video SDK
        role: 1 = Host, 0 = Participant
        """
        sdk_key = config('ZOOM_SDK_KEY')
        sdk_secret = config('ZOOM_SDK_SECRET')
        
        # Token expira en 2 horas
        iat = int(time.time())
        exp = iat + 60 * 60 * 2
        
        payload = {
            'app_key': sdk_key,
            'tpc': session_name,  # Topic (session name)
            'role_type': role,
            'version': 1,
            'iat': iat,
            'exp': exp
        }
        
        token = jwt.encode(payload, sdk_secret, algorithm='HS256')
        return token
    
    @staticmethod
    def create_session_config(clase_zoom, user_name, is_host=False):
        """
        Crea la configuración completa para unirse a una sesión de Zoom
        """
        role = 1 if is_host else 0
        signature = ZoomService.generate_signature(clase_zoom.session_name, role)
        
        return {
            'signature': signature,
            'sdkKey': config('ZOOM_SDK_KEY'),
            'sessionName': clase_zoom.session_name,
            'userName': user_name,
            'password': clase_zoom.password,
            'role': role
        }
