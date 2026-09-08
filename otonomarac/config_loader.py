"""
config.yaml dosyasını okur ve yazar.

Yol, çalışma dizinine değil bu dosyanın konumuna göre çözülür; böylece
main.py hangi klasörden çalıştırılırsa çalıştırılsın config bulunur.
"""
import os
import yaml

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "config.yaml")


def load_config(path=None):
    if path is None:
        path = DEFAULT_PATH
    with open(path, "r") as f:
        cfg = yaml.safe_load(f)
    return cfg


def save_config(cfg, path=None):
    if path is None:
        path = DEFAULT_PATH
    with open(path, "w") as f:
        yaml.safe_dump(cfg, f, default_flow_style=False,
                       allow_unicode=True, sort_keys=False)
