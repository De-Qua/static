# DeQua Static

Servizio per gestire i file dei grafi e della marea.

Il servizio è pensato per girare su Docker solo per coerenza con la struttura degli altri servizi. Il codice si trova dentro `app/`

Le due funzioni python principali sono `update_graphs_db.py` e `update_high_tide_level_db`

Le configurazioni (principalmente per quanto riguarda il database) sono su un file `.env`. Prima di lanciare gli script generate un file `.env` a partire dal file `.env.example`.

Per lanciarlo come docker i comandi sono:
```bash
# Update graphs
docker compose run --rm dq_static python /app/update_graphs_db.py
# Update high tide
docker compose run --rm dq_static python /app/update_high_tide_level_db.py
```

Il sistema è pensato per essere lanciato periodicamente. Il modo più semplice è creare un cronjon sul server (ovviamente da aggiustare il path con il path di questa cartella):

```bash
# crontab -e sull'host
0 2 * * * cd /path/to/docker-compose && docker compose run --rm dq_static python /app/update_graphs_db.py
2-59/5 * * * * cd /path/to/docker-compose && docker compose run --rm dq_static python /app/update_graphs_db.py
```