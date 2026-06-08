# 🏎️ Peacock Elettrica - Sistema di Telemetria Cloud FSAE

![AWS](https://img.shields.io/badge/AWS-%23FF9900.svg?style=for-the-badge&logoColor=white) ![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) ![JavaScript](https://img.shields.io/badge/javascript-%23323330.svg?style=for-the-badge&logo=javascript&logoColor=%23F7DF1E) ![MQTT](https://img.shields.io/badge/MQTT-660066?style=for-the-badge&logo=mqtt&logoColor=white) ![CSS](https://img.shields.io/badge/css-663399?style=for-the-badge&logo=css&logoColor=white) ![HTML5](https://img.shields.io/badge/html-E34F26?style=for-the-badge&logo=html5&logoColor=white)

---

> 🌐 **Lingua / Language:** 🇮🇹 **Italiano** | 🇬🇧 [English](readme.md)
>
> 📖 Per guide sulla configurazione dettagliate, diagrammi architetturali e indirizzi API, consulta la **[Wiki del Progetto](../../wiki)**.

---

Infrastruttura cloud serverless e dashboard web per l'acquisizione, l'elaborazione e la visualizzazione in tempo reale della telemetria della monoposto elettrica **Peacock Elettrica** Formula Student, sviluppato dal **[Polimarche Racing Team](https://www.polimarcheracingteam.com/it/)**.

Sviluppato nell'ambito del corso di **Architetture dei Calcolatori e Cloud Computing (ACCC)** - **Università Politecnica delle Marche (UNIVPM)**, A.A. 2025–26.

> ⚠️ Questo è un progetto universitario. Certificati, endpoint AWS e chiavi di accesso **non** sono inclusi nel repository.

---

## 📌 Panoramica

Il sistema gestisce il flusso completo dei dati dal ricevitore a bordo pista al browser web dei membri del team, garantendo latenza bassa, alta scalabilità e accesso crittograficamente sicuro - senza esporre alcuna credenziale sul frontend.

L'architettura disaccoppia l'acquisizione fisica dei dati dalla loro distribuzione globale, sfruttando il paradigma serverless di AWS:

1. **Acquisizione Edge:** La vettura trasmette i dati tramite modulo LoRa. Un ricevitore a bordo pista (UART/SPI) raccoglie i pacchetti grezzi.
2. **Bridge Python:** Uno script Python locale funge da bridge - decodifica i payload seriali e li pubblica su **AWS IoT Core** tramite connessione MQTT cifrata TLS (porta 8883), utilizzando certificati X.509 per l'autenticazione del dispositivo.
3. **Distribuzione Cloud:** AWS IoT Core funge da broker MQTT, riceve tutti i messaggi di telemetria sul topic `P5/telemetry` e li rende disponibili a tutti i subscriber connessi.
4. **Dashboard Web:** Gli utenti si autenticano tramite matricola. Il browser apre poi una connessione diretta **MQTT over WebSockets** allo stesso broker AWS IoT Core, ricevendo i dati a latenza quasi zero.

---

## 🛠️ Servizi AWS

| Servizio | Ruolo |
|---|---|
| ![IoT Core](https://img.shields.io/badge/IoT%20Core-1A9C3E?style=flat-square&logoColor=white) | Broker MQTT - acquisisce la telemetria e la instrada ai client web connessi |
| ![API Gateway](https://img.shields.io/badge/API%20Gateway-FF4F8B?style=flat-square&logoColor=white) | Espone l'endpoint REST sicuro per il login chiamato dalla dashboard |
| ![Lambda](https://img.shields.io/badge/Lambda-FF9900?style=flat-square&logoColor=white) | Logica di autenticazione - verifica l'utente e genera l'URL WebSocket pre-firmato |
| ![DynamoDB](https://img.shields.io/badge/DynamoDB-4053D6?style=flat-square&logoColor=white) | Database NoSQL che memorizza la whitelist delle matricole autorizzate (`team-members-pE`) |
| ![S3](https://img.shields.io/badge/S3-569A31?style=flat-square&logoColor=white) | Hosting statico privato per i file HTML, CSS e JS della dashboard |
| ![CloudFront](https://img.shields.io/badge/CloudFront-8C4FFF?style=flat-square&logoColor=white) | CDN - espone S3 su HTTPS con caching globale |
| ![IAM](https://img.shields.io/badge/IAM-DD344C?style=flat-square&logoColor=white) | Ruolo di esecuzione assegnato alla Lambda - garantisce accesso con privilegi minimi a DynamoDB e IoT Core |

---

## 🔐 Autenticazione & Sicurezza

Il progetto implementa **AWS Signature Version 4 (SigV4)** per la connessione WebSocket, rendendo l'architettura *Secure by Design*:

1. **Nessun dato sensibile sul frontend** - la dashboard JavaScript non contiene alcuna credenziale AWS (access key, secret key o token). L'unico riferimento AWS nel codice client è l'URL pubblico dell'endpoint API Gateway, intenzionalmente esposto in quanto punto di ingresso non autenticante, protetto dalla Lambda stessa.
2. **Verifica dell'identità** - l'utente invia la propria matricola UNIVPM. La richiesta raggiunge API Gateway e attiva la Lambda.
3. **Controllo degli accessi** - Lambda interroga DynamoDB. Se la matricola non è nella whitelist, l'accesso viene negato immediatamente con HTTP 403.
4. **Derivazione delle chiavi (HMAC-SHA256)** - se autorizzata, Lambda legge le credenziali del proprio ruolo IAM di esecuzione (iniettate automaticamente dal runtime AWS) e le usa per firmare un URL pre-firmato temporaneo per IoT Core.
5. **Connessione diretta** - Lambda restituisce l'URL firmato al browser. Il frontend apre il WebSocket; AWS IoT Core ricalcola la firma e, se valida, autorizza la connessione.

---

## 📊 Dashboard Web

L'applicazione a pagina singola è costruita con HTML, CSS e JavaScript. Funzionalità principali:

- **Telemetria in Tempo Reale** - aggiornamenti DOM istantanei per velocità, temperature (motori, inverter, pacco batteria), tensioni (HV/LV) e State of Charge (SoC).
- **Tracking GPS Live** - mappa interattiva con `Leaflet.js` e layer tile commutabili (OpenStreetMap, Satellite), che traccia il marcatore dell'auto in tempo reale.
- **Segnali di Diagnostica** - monitoraggio in tempo reale di 9 flag di errore (sovracorrente, sovratensione, guasti ai sensori, ecc.) tramite analisi bitmask dei payload in ingresso.
- **Heartbeat di Connessione** - indicatore visivo Online/Offline basato sui timestamp dei messaggi; passa a Offline dopo 30 secondi senza dati.
- **Login Overlay** - pannello di autenticazione basato su matricola prima della visualizzazione dei dati di telemetria.

---

## 🗂️ Struttura del Progetto

```
AWS_Polimarche/
├── IoT-Core_AWS-thread.py        # Bridge Python principale: produttore/publisher multi-thread
|
├── .gitignore
|
├── certs/                        # Certificati TLS (NON inclusi nel repo)
│   ├── AmazonRootCA1.pem
│   ├── <CERT_ID>-certificate.pem.crt
│   └── <CERT_ID>-private.pem.key
│
├── lambda/
│   └── lambda_function.py  # Lambda di produzione (SigV4 + autenticazione DynamoDB)
│
├── html/
│   ├── index.html                # Dashboard & entry point web
│   └── static/
│       ├── css/style-v2.css      # Stile della dashboard
│       ├── js/script.js          # Client MQTT, mappa Leaflet, rendering telemetria
│       └── img/                  # Icona auto, loghi del team
│
├── tools/
│   ├── DatabaseUploader.py       # Tool CLI: caricamento matricole da CSV -> DynamoDB
│   ├── DatabaseRemove.py         # Tool CLI: rimozione matricole da CSV -> DynamoDB
│   └── whitelist.csv             # CSV di esempio dei membri del team (gitignored)
│
└── docs/
    └── iot-dg-1827.pdf           # Riferimento alla guida AWS IoT Core Developer Guide
```

---

## 🚀 Configurazione

### Prerequisiti

```bash
pip install -r requirements.txt
```

Le credenziali AWS devono essere configurate (tramite `aws configure` o variabili d'ambiente) per la Lambda e i tool DynamoDB.

### 1 - Avviare il Bridge Python (modalità mock, senza hardware)

```bash
# Modifica il blocco CONFIGURAZIONE in cima a IoT-Core_AWS-thread.py:
#   MODE = "random"
#   AWS_ENDPOINT = "<TUO_AWS_IOT_ENDPOINT>"
#   PATH_ROOT_CA / PATH_CERT / PATH_KEY = percorsi ai tuoi certificati

python IoT-Core_AWS-thread.py
```

### 2 - Avviare il Bridge Python (hardware seriale reale)

```bash
# Modifica IoT-Core_AWS-thread.py:
#   MODE = "serial"
#   SERIAL_PORT = "COMx"   # oppure /dev/ttyUSBx su Linux

python IoT-Core_AWS-thread.py
```

### 3 - Gestire la Whitelist DynamoDB

I tool richiedono l'**AWS CLI** e credenziali con accesso DynamoDB.

Installa la AWS CLI se non è già presente: [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

Configura le credenziali una volta sola:

```bash
aws configure
# AWS Access Key ID: <la tua chiave>
# AWS Secret Access Key: <il tuo segreto>
# Default region: us-east-1
```

Il file `whitelist.csv` nel repo è da intendersi come esempio: quello reale è gitignored.

```bash
# Aggiunge i membri dal CSV (richiede la colonna MATRICOLA)
python tools/DatabaseUploader.py tools/whitelist.csv

# Rimuove i membri dal CSV
python tools/DatabaseRemove.py tools/whitelist.csv
```

### 4 - Dashboard

La dashboard è distribuita tramite **Amazon S3 + CloudFront** ed è accessibile solo da domini autorizzati. API Gateway e Lambda sono configurati per accettare richieste CORS esclusivamente da quelle origini - le richieste da qualsiasi altro host (incluso `localhost`) vengono rifiutate prima di raggiungere la logica di autenticazione.

L'istanza live è disponibile su: **[livedata.polimarcheracingteam.com](https://livedata.polimarcheracingteam.com)**

---

## 🖼️ Anteprima Dashboard

<p align="center">
  <img src="docs/final_layout_login.PNG" width="700" alt="Schermata di login"/>
  <br><br>
  <img src="docs/final_layout.PNG" width="700" alt="Dashboard principale"/>
</p>

---

## 📈 Stato di Sviluppo

| Funzionalità | Stato |
|---|---|
| Bridge Python MQTT - modalità random (mock) | ✅ Completato |
| Bridge Python MQTT - modalità serial (hardware) | ✅ Completato |
| Test fisico: ricezione LoRa -> UART/SPI -> lettura seriale | ⏳ In attesa di hardware |
| Architettura produttore/publisher multi-thread | ✅ Completato |
| Publish su singolo topic con payload parziale per tipo di messaggio | ✅ Completato |
| Configurazione broker AWS IoT Core | ✅ Completato |
| Funzione Lambda di autenticazione (SigV4) | ✅ Completato |
| Whitelist matricole DynamoDB | ✅ Completato |
| Endpoint REST API Gateway | ✅ Completato |
| Hosting statico S3 + CloudFront | ✅ Completato |
| Login overlay dashboard (autenticazione matricola) | ✅ Completato |
| Visualizzazione telemetria in tempo reale | ✅ Completato |
| Tracking GPS live con Leaflet.js | ✅ Completato |
| Matrice flag di errore diagnostici | ✅ Completato |
| Monitor heartbeat di connessione | ✅ Completato |
| Tool CLI di gestione DynamoDB | ✅ Completato |

---

## 🔄 Riferimenti & Risorse

- [aws-samples/aws-iot-wss-ts-client](https://github.com/aws-samples/aws-iot-wss-ts-client) - Client TypeScript di riferimento per AWS IoT Core over WebSockets (SigV4), usato come punto di partenza per la connessione MQTT lato browser.
- [AWS IoT Core Developer Guide](https://docs.aws.amazon.com/iot/latest/developerguide/what-is-aws-iot.html) - Documentazione ufficiale per MQTT, certificati X.509 e policy IoT.
- [AWS Signature Version 4 signing process](https://docs.aws.amazon.com/general/latest/gr/signature-version-4.html) - Riferimento per la catena di derivazione delle chiavi HMAC-SHA256 implementata nella Lambda.
- [AWS Boto3](https://docs.aws.amazon.com/boto3/) - SDK Python di AWS.
- [Leaflet.js](https://leafletjs.com/) - Libreria JavaScript open-source per mappe interattive.
- [MQTT.js](https://github.com/mqttjs/MQTT.js) - Libreria client MQTT usata nella dashboard browser.
- [HiveMQ](https://www.hivemq.com/blog/implementing-mqtt-in-python/) - Guida Getting Started per l'implementazione di MQTT in Python.
- [Magnific (ex Freepik.com)](https://www.magnific.com/it) - Tutte le icone utilizzate nella dashboard web.
- [Shields.io](https://shields.io/) - Per gli elementi estetici del repository (tramite [SimpleIcons](https://simpleicons.org)).

---

## 📄 Licenza

Questo progetto è distribuito con licenza **[Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)](https://creativecommons.org/licenses/by-nc/4.0/)**.

Sei libero di usare, modificare e distribuire questo lavoro per scopi non commerciali, purché venga dato il giusto credito agli autori.

Sviluppato per scopi accademici presso **Polimarche Racing Team | Università Politecnica delle Marche (UNIVPM)**

---

## 📬 Contatti

Per domande o collaborazioni, contatta:

- 📧 `zingaale@gmail.com`