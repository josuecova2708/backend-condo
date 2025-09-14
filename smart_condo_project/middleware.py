import logging
import time

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware:
    """Middleware para logging detallado de todas las requests"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log de request entrante
        start_time = time.time()

        logger.info(f"=== INCOMING REQUEST ===")
        logger.info(f"Method: {request.method}")
        logger.info(f"Path: {request.path}")
        logger.info(f"Full URL: {request.build_absolute_uri()}")
        logger.info(f"User Agent: {request.META.get('HTTP_USER_AGENT', 'N/A')}")
        logger.info(f"Origin: {request.META.get('HTTP_ORIGIN', 'N/A')}")
        logger.info(f"Referer: {request.META.get('HTTP_REFERER', 'N/A')}")
        logger.info(f"X-Forwarded-For: {request.META.get('HTTP_X_FORWARDED_FOR', 'N/A')}")
        logger.info(f"X-Forwarded-Proto: {request.META.get('HTTP_X_FORWARDED_PROTO', 'N/A')}")
        logger.info(f"Remote Address: {request.META.get('REMOTE_ADDR', 'N/A')}")

        if request.headers:
            logger.info(f"Headers: {dict(request.headers)}")

        response = self.get_response(request)

        # Log de response
        duration = time.time() - start_time
        logger.info(f"=== OUTGOING RESPONSE ===")
        logger.info(f"Status: {response.status_code}")
        logger.info(f"Duration: {duration:.3f}s")
        logger.info(f"Response headers: {dict(response.items())}")
        logger.info(f"========================")

        return response