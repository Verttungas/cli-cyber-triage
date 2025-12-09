import os
import boto3
import requests
import json
from datetime import datetime, timedelta
import logging
from db_manager import DatabaseManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CYBERHAVEN_TOKEN = os.getenv("CYBERHAVEN_API_KEY")
CYBERHAVEN_BASE_URL = os.getenv("CYBERHAVEN_API_URL", "https://payclip.cyberhaven.io/public")
BUCKET_NAME = os.getenv("AWS_S3_BUCKET", "clip-cyberhaven-upload")
DOWNLOAD_DIR = os.getenv("EVIDENCE_DIR", "./evidencia_temp")

if not CYBERHAVEN_TOKEN:
    logger.warning("CYBERHAVEN_API_KEY no está configurada. El script fallará si intenta conectar.")

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)
    logger.info(f"Directorio creado: {DOWNLOAD_DIR}")

def get_token():
    if not CYBERHAVEN_TOKEN:
        return None
    url = f"{CYBERHAVEN_BASE_URL}/v2/auth/token/access"
    try:
        logger.info("Obteniendo access token de Cyberhaven...")
        resp = requests.post(url, json={"refresh_token": CYBERHAVEN_TOKEN}, timeout=10)
        resp.raise_for_status()
        logger.info("Token obtenido correctamente")
        return resp.json()['access_token']
    except Exception as e:
        logger.error(f"Error obteniendo token: {e}")
        return None


def download_from_s3(file_hash, original_ext):
    s3 = boto3.client('s3')
    try:
        logger.debug(f"Buscando en S3: {BUCKET_NAME}/{file_hash[:15]}...")
        response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=file_hash)
        if 'Contents' not in response:
            logger.warning(f"No se encontró archivo con hash: {file_hash[:15]}")
            return None

        target_key = None
        for obj in response['Contents']:
            key = obj['Key']
            if not key.endswith('.html') and not key.endswith('.json'):
                target_key = key
                break

        if target_key:
            local_filename = f"{file_hash}.{original_ext}"
            local_path = os.path.join(DOWNLOAD_DIR, local_filename)

            logger.info(f"Descargando: {target_key} -> {local_filename}")
            s3.download_file(BUCKET_NAME, target_key, local_path)
            logger.info(f"Descargado: {local_path}")
            return local_path
        else:
            logger.warning(f"No se encontró archivo válido para hash: {file_hash[:15]}")

    except Exception as e:
        logger.error(f"Error descargando desde S3: {e}")
    return None

def main():
    logger.info("="*60)
    logger.info("CYBER-TRIAGE: EVIDENCE DOWNLOADER")
    logger.info("="*60)
    
    db = DatabaseManager()
    
    token = get_token()
    if not token:
        logger.error("No se pudo obtener token. Abortando.")
        return

    days_back = int(os.getenv("INCIDENT_DAYS_BACK", "3"))
    start_date = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y-%m-%dT%H:%M:%SZ')
    logger.info(f"Buscando incidentes desde: {start_date} ({days_back} días atrás)")

    try:
        resp = requests.post(
            f"{CYBERHAVEN_BASE_URL}/v2/incidents/list",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "page_request": {"size": 20, "sort_by": "event_time"},
                "filter": {"start_time": start_date}
            },
            timeout=30
        )
        resp.raise_for_status()
        incidents = resp.json().get('resources', [])
        logger.info(f"Incidentes encontrados: {len(incidents)}")
        
        for inc in incidents:
            incident_id = inc.get('id')
            file_info = inc.get('file_info', {})
            file_name = file_info.get('name', 'unknown')
            file_hash = file_info.get('content_hash')
            file_size = file_info.get('size', 0)
            user_email = inc.get('user', {}).get('email', 'unknown')
            
            if db.get_incident(incident_id):
                logger.info(f"Incidente {incident_id} ya existe en DB. Saltando.")
                continue
            
            file_path = None
            if file_hash:
                ext = file_name.split('.')[-1] if '.' in file_name else 'bin'
                file_path = download_from_s3(file_hash, ext)
            
            incident_data = {
                'incident_id': incident_id,
                'file_name': file_name,
                'file_path': file_path,
                'file_type': file_name.split('.')[-1] if '.' in file_name else 'unknown',
                'file_size': file_size,
                'user_email': user_email,
                'cyberhaven_data': inc
            }
            
            db.insert_incident(incident_data)
            
    except Exception as e:
        logger.error(f"Error obteniendo incidentes: {e}")
        return

if __name__ == "__main__":
    main()