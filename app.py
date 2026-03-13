# -*- coding: utf-8 -*-
"""
Created on Thu Mar 12 21:25:26 2026

@author: MSI
"""
from pathlib import Path
import sys

# Add src to path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# Now imports will work
from src.discharge import DischargeCalculator
from src.rainfall import RainfallFrequencyAnalysis
from src.reporter import ReportGenerator
