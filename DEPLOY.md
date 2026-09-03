# Deployment

1. `sudo mkdir -p /srv/docker/Domoticz-MySkoda && cd /srv/docker/Domoticz-MySkoda`
2. Copy this release into that directory.
3. `cp .env.example .env && nano .env`
4. Set your MyŠkoda credentials and Domoticz password. Do not commit `.env`.
5. Edit `config/vehicles.csv` and put the two VINs into the matching rows.
6. Keep `DEVICES_JSON_PATH=/app/state/devices.json`.
7. Verify `state/devices.json` matches your IDX mapping.
8. In Domoticz, IDX 1473/1474 and 1485/1486 should be Custom Counter devices. Inspection IDX 1475/1487 is also an absolute Custom Counter.
9. Build:

```bash
docker compose build --no-cache
```

10. Verify the installed library:

```bash
docker compose run --rm --no-deps --entrypoint python domoticz-myskoda \
  -c 'import inspect; from myskoda import MySkoda; print(inspect.signature(MySkoda.__init__))'
```

11. Start:

```bash
docker compose up -d
docker compose logs -f --tail=100 domoticz-myskoda
```

12. Check:

```bash
docker compose ps
```

13. Test Domoticz authentication/update:

```bash
curl -i -u 'domotic_skoda_user:domoticz_skoda_password' \
  'http://domoticz_ip:domoticz_httpport/json.htm?type=command&param=udevice&idx=1474&nvalue=0&svalue=12345'
```

Expected JSON status: `OK`. If HTTP 401 occurs, the Domoticz `skoda` account lacks the required device-update permission.

14. Logs:

```bash
docker compose logs --tail=200 domoticz-myskoda
```

15. Update later:

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
docker compose logs -f --tail=100 domoticz-myskoda
```
