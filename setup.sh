#!/bin/bash
# Utwórz i aktywuj środowisko wirtualne
python3 -m venv venv
source venv/bin/activate

pip install -e ".[dev,all_db]"