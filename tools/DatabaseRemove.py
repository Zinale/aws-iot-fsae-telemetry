"""
DatabaseRemove.py
-----------------
Legge un file CSV e rimuove le matricole dalla colonna "MATRICOLA"
dalla tabella DynamoDB 'team-members-pE'.

Utilizzo:
    python DatabaseRemove.py <percorso_file.csv>

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
        print("Utilizzo: python DatabaseRemove.py <percorso_file.csv>")
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
            rows = [row['MATRICOLA'].strip().upper() for row in reader if row['MATRICOLA'].strip()]
    except FileNotFoundError:
        print(f"Errore: file '{csv_path}' non trovato.")
        sys.exit(1)

    if not rows:
        print("Nessuna matricola trovata nel file.")
        sys.exit(0)

    print(f"Stai per eliminare {len(rows)} matricole da '{TABLE_NAME}'.")
    conferma = input("Confermi? (s/N): ").strip().lower()
    if conferma != 's':
        print("Operazione annullata.")
        sys.exit(0)

    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    table    = dynamodb.Table(TABLE_NAME)

    rimosse = 0
    errori  = 0

    print(f"Rimozione in corso...")

    with table.batch_writer() as batch:
        for matricola in rows:
            try:
                batch.delete_item(Key={'matricola': matricola})
                rimosse += 1
            except ClientError as e:
                print(f"  Errore su '{matricola}': {e.response['Error']['Message']}")
                errori += 1

    print(f"\nFatto! Rimosse: {rimosse} | Errori: {errori}")

if __name__ == '__main__':
    main()
