#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script para ejecutar decision_engine sin interferencias."""

from src.decision_engine import main
import sys

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    main("data/processed/daily.csv", "data/processed")
    print("✅ Decision engine completado!")

