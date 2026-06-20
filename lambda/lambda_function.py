import json
import boto3
import urllib.parse
import hmac
import hashlib
from datetime import datetime

dynamodb = boto3.resource('dynamodb')

# ================= CONFIGURAZIONE =================
TABLE_NAME = 'team-members-pE'

#config.py
IOT_ENDPOINT = 'CENSORED'
REGION = 'us-east-1'
# ==================================================

def lambda_handler(event, context):
    # Estrae l'Origin dalla richiesta per il controllo CORS 
    headers = event.get('headers', {})
    request_origin = headers.get('origin') or headers.get('Origin') or ''
    try:
        if 'body' in event and isinstance(event['body'], str):
            body = json.loads(event['body'])
        else:
            body = event
            
        matricola = body.get('matricola')
        print(f"Tentativo di accesso con matricola: {matricola}")

        if not matricola:
            print("Richiesta respinta: matricola vuota.")
            return response(400, "Errore: Inserire una matricola UNIVPM.")

        # Controlla la matricola in DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        db_response = table.get_item(Key={'matricola': matricola})

        if 'Item' not in db_response:
            print(f"Accesso negato: la matricola {matricola} non è nel database.")
            return response(403, "Accesso negato: Matricola non autorizzata dal team.", request_origin)

        # Usa le credenziali del ruolo della Lambda 
        session = boto3.Session()
        creds = session.get_credentials().get_frozen_credentials()

        # Genera l'URL Sicuro (Pre-Signed) per MQTT over WebSockets
        ws_url = get_presigned_url(
            endpoint=IOT_ENDPOINT,
            region=REGION,
            access_key=creds.access_key,
            secret_key=creds.secret_key,
            token=creds.token
        )

        print(f"Accesso consentito per {matricola}. URL generato con successo.")
        return response(200, {"url": ws_url}, request_origin)

    except Exception as e:
        print(f"Errore: {str(e)}")
        return response(500, "Errore interno del server.")


# ---- Algoritmo  AWS SigV4 ----
def get_presigned_url(endpoint, region, access_key, secret_key, token):
    service, algorithm = 'iotdevicegateway', 'AWS4-HMAC-SHA256'
    t = datetime.utcnow()
    amz_date = t.strftime('%Y%m%dT%H%M%SZ')
    datestamp = t.strftime('%Y%m%d')
    credential_scope = f"{datestamp}/{region}/{service}/aws4_request"

    canonical_querystring  = f"X-Amz-Algorithm={algorithm}"
    canonical_querystring += f"&X-Amz-Credential={urllib.parse.quote(access_key + '/' + credential_scope, safe='')}"
    canonical_querystring += f"&X-Amz-Date={amz_date}"
    canonical_querystring += f"&X-Amz-Expires=86400"
    canonical_querystring += f"&X-Amz-SignedHeaders=host"

    canonical_headers = f"host:{endpoint}\n"
    payload_hash = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    canonical_request = f"GET\n/mqtt\n{canonical_querystring}\n{canonical_headers}\nhost\n{payload_hash}"
    string_to_sign = f"{algorithm}\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"

    def sign(key, msg): return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

    k_signing = sign(sign(sign(sign(('AWS4' + secret_key).encode('utf-8'), datestamp), region), service), 'aws4_request')
    signature = hmac.new(k_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

    canonical_querystring += f"&X-Amz-Signature={signature}"
    if token:
        canonical_querystring += f"&X-Amz-Security-Token={urllib.parse.quote(token, safe='')}"
    return f"wss://{endpoint}/mqtt?{canonical_querystring}"


def response(status_code, body_data, request_origin = ""):
    allowed_origins = [
        'https://livedata.polimarcheracingteam.com',
        'https://livedata.polimarcheracingteam.it',
        'https://livedata.alessandrozingaretti.cloud'
    ]

    cors_origin = request_origin if request_origin in allowed_origins else ''

    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': cors_origin, 
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,POST'
        },
        'body': json.dumps(body_data)
    }


