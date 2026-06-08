"""
DatabaseUploader.py
-------------------
Legge un file CSV e carica le matricole dalla colonna "MATRICOLA"
nella tabella DynamoDB 'team-members-pE'.

Utilizzo:
    python DatabaseUploader.py <percorso_file.csv>

Prerequisiti:
    pip install boto3
    aws configure  (oppure variabili d'ambiente AWS_ACCESS_KEY_ID, ecc.)
"""

import sys
import csv
import boto3
from botocore.exceptions import ClientError

TABLE_NAME = 'team-members-pE'
REGION     = 'us-east-1'

def main():
    if len(sys.argv) < 2:
        print("Utilizzo: python DatabaseUploader.py <percorso_file.csv>")
        sys.exit(1)

    csv_path = sys.argv[1]

    try:
        with open(csv_path, newline='', encoding='utf-8-sig') as f:
            sample = f.read(4096)
            f.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|')
            reader = csv.DictReader(f, dialect=dialect)
            if 'MATRICOLA' not in reader.fieldnames:
                print(f"Errore: colonna 'MATRICOLA' non trovata nel CSV.")
                print(f"Colonne trovate: {reader.fieldnames}")
                sys.exit(1)
            OPTIONAL_FIELDS = {'NOME': 'nome', 'COGNOME': 'cognome', 'REPARTO': 'reparto'}
            available = {csv_col: db_key for csv_col, db_key in OPTIONAL_FIELDS.items()
                         if csv_col in reader.fieldnames}
            rows = []
            for row in reader:
                matricola = row['MATRICOLA'].strip()
                if not matricola:
                    continue
                item = {'matricola': matricola.upper()}
                for csv_col, db_key in available.items():
                    val = row[csv_col].strip()
                    if val:
                        item[db_key] = val.upper()
                rows.append(item)
    except FileNotFoundError:
        print(f"Errore: file '{csv_path}' non trovato.")
        sys.exit(1)

    if not rows:
        print("Nessuna matricola trovata nel file.")
        sys.exit(0)

    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    table    = dynamodb.Table(TABLE_NAME)

    inserite = 0
    errori   = 0

    print(f"Caricamento di {len(rows)} voci in '{TABLE_NAME}'...")

    with table.batch_writer() as batch:
        for item in rows:
            try:
                batch.put_item(Item=item)
                inserite += 1
            except ClientError as e:
                print(f"  Errore su '{item.get('matricola')}': {e.response['Error']['Message']}")
                errori += 1

    print(f"\nFatto! Inserite: {inserite} | Errori: {errori}")

if __name__ == '__main__':
    main()