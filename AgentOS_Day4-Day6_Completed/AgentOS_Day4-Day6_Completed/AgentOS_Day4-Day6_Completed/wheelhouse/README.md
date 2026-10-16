# Offline Python wheelhouse

This directory is intentionally empty in the source archive because wheels must match the target OS, CPU architecture, and Python version. Before going offline, populate it on a matching machine:

```bash
python -m pip download -r requirements.txt -d wheelhouse
```

Then transfer the entire repository including the wheelhouse to the offline target. `setup.sh` uses `pip --no-index`; it will not silently download from the internet.
